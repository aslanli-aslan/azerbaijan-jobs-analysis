from pathlib import Path

ROOT = Path(__file__).parent.parent.parent

RAW_DATA = ROOT / "data/raw/vacancies.db"
CLEAN_DATA = ROOT / "data/processed/clean_vacancies.db"
FINAL_DATA = ROOT / "data/processed/final_vacancies.db"
SAMPLE_DATA = ROOT / "data/labeled/sample.csv"
LABELED_DATA = ROOT / "data/labeled/labeled_sample.csv"
