"""
jobsearch.az vacancy scraper
- SQLite-backed: only new vacancies are inserted on each run
- Parallel page fetching + parallel detail fetching
- Retry logic with exponential back-off
- Safe to run daily via cron / Task Scheduler
"""

import logging
import sqlite3
import contextlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from urllib3.util.retry import Retry

import requests
from requests.adapters import HTTPAdapter

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BASE_URL = (
    "https://jobsearch.az/api-az/vacancies-az"
    "?hl=az&q=&posted_date=&seniority=&categories=&industries="
    "&ads=&location=&job_type=&salary=&order_by="
)
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://jobsearch.az/",
}

MAX_WORKERS = 20  # parallel detail fetches
PAGE_WORKERS = 5  # parallel listing-page fetches
TIMEOUT = 10  # seconds per request
DB_PATH = Path("vacancies.db")


# ---------------------------------------------------------------------------
# HTTP session with retry + connection pooling
# ---------------------------------------------------------------------------
def make_session() -> requests.Session:
    retry = Retry(
        total=4,
        backoff_factor=0.5,  # 0.5 s, 1 s, 2 s, 4 s
        status_forcelist={429, 500, 502, 503, 504},
        allowed_methods={"GET"},
    )
    adapter = HTTPAdapter(
        max_retries=retry,
        pool_connections=PAGE_WORKERS + 2,
        pool_maxsize=MAX_WORKERS + PAGE_WORKERS + 4,
    )
    s = requests.Session()
    s.headers.update(HEADERS)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


SESSION = make_session()


# ---------------------------------------------------------------------------
# HTML stripping
# ---------------------------------------------------------------------------
class _Stripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts).strip()


def strip_html(html: str) -> str:
    if not html:
        return ""
    p = _Stripper()
    p.feed(html)
    return p.get_text()


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
CREATE_SQL = """
CREATE TABLE IF NOT EXISTS vacancies (
    id            INTEGER PRIMARY KEY,
    title         TEXT,
    company       TEXT,
    company_id    INTEGER,
    salary        TEXT,
    category      TEXT,
    created_at    TEXT,
    deadline_at   TEXT,
    view_count    INTEGER,
    direct_apply  INTEGER,
    url           TEXT,
    description   TEXT,
    fetched_at    TEXT DEFAULT (datetime('now'))
);
"""


@contextlib.contextmanager
def get_db(path: Path = DB_PATH):
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")  # better concurrency
    conn.execute(CREATE_SQL)
    conn.commit()
    try:
        yield conn
    finally:
        conn.close()


def existing_ids(conn: sqlite3.Connection) -> set[int]:
    rows = conn.execute("SELECT id FROM vacancies").fetchall()
    return {r[0] for r in rows}


def insert_vacancies(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """Insert rows, skipping any whose id already exists. Returns insert count."""
    sql = """
        INSERT OR IGNORE INTO vacancies
            (id, title, company, company_id, salary, category,
             created_at, deadline_at, view_count, direct_apply, url, description)
        VALUES
            (:id, :title, :company, :company_id, :salary, :category,
             :created_at, :deadline_at, :view_count, :direct_apply, :url, :description)
    """
    conn.executemany(sql, rows)
    conn.commit()
    return conn.execute("SELECT changes()").fetchone()[0]


# ---------------------------------------------------------------------------
# Fetching helpers
# ---------------------------------------------------------------------------
def _fetch_page(url: str) -> dict | None:
    try:
        r = SESSION.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        log.error("Listing page failed (%s): %s", url, exc)
        return None


def _fetch_detail(slug: str) -> dict | None:
    try:
        r = SESSION.get(
            f"https://jobsearch.az/api-az/vacancies-az/{slug}?hl=az",
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        log.warning("Detail fetch failed for '%s': %s", slug, exc)
        return None


def _flatten(v: dict) -> dict:
    return {
        "id": v.get("id"),
        "title": v.get("title"),
        "company": v.get("company", {}).get("title"),
        "company_id": v.get("company", {}).get("id"),
        "salary": v.get("salary"),
        "category": v.get("category", {}).get("title"),
        "created_at": v.get("created_at"),
        "deadline_at": v.get("deadline_at"),
        "view_count": v.get("view_count"),
        "direct_apply": v.get("direct_apply"),
        "url": f"https://jobsearch.az/vacancies/{v.get('slug')}",
        "description": strip_html(v.get("text", "")),
    }


# ---------------------------------------------------------------------------
# Core scraping logic
# ---------------------------------------------------------------------------
def collect_new_slugs(known_ids: set[int]) -> list[str]:
    """
    Walk listing pages and return slugs whose IDs are not yet in the DB.
    Stops early once a full page consists entirely of known IDs (saves time
    on incremental daily runs once the bulk of vacancies are already stored).
    """
    new_slugs: list[str] = []
    url: str | None = BASE_URL
    page_num = 0

    while url:
        data = _fetch_page(url)
        if data is None:
            break

        items = data.get("items", [])
        page_num += 1
        page_ids = {item["id"] for item in items}
        novel = page_ids - known_ids

        new_slugs.extend(item["slug"] for item in items if item["id"] in novel)
        log.info(
            "Page %d: %d items, %d new (running total: %d)",
            page_num,
            len(items),
            len(novel),
            len(new_slugs),
        )

        # Early-exit: if this page had zero new IDs the feed is ordered
        # newest-first and we've caught up.
        if len(novel) == 0:
            log.info("All items on page %d already in DB — stopping early.", page_num)
            break

        url = data.get("next")

    return new_slugs


def fetch_details_parallel(slugs: list[str]) -> list[dict]:
    """Fetch vacancy detail pages in parallel, return flattened dicts."""
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_fetch_detail, slug): slug for slug in slugs}
        for future in as_completed(futures):
            vacancy = future.result()
            if vacancy:
                flat = _flatten(vacancy)
                results.append(flat)
                log.info(
                    "%s | %s | %s",
                    flat.get("company", "?"),
                    flat.get("title", "?"),
                    flat.get("salary", "—"),
                )
    return results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    log.info("Starting scraper. DB: %s", DB_PATH.resolve())

    with get_db() as conn:
        known = existing_ids(conn)
        log.info("Known vacancies in DB: %d", len(known))

        new_slugs = collect_new_slugs(known)
        log.info("New slugs to fetch: %d", len(new_slugs))

        if not new_slugs:
            log.info("Nothing new — exiting.")
            return

        rows = fetch_details_parallel(new_slugs)
        inserted = insert_vacancies(conn, rows)

    log.info("Done. Fetched %d details, inserted %d new rows.", len(rows), inserted)


if __name__ == "__main__":
    main()
