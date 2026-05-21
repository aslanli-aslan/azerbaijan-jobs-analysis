import sqlite3
import pandas as pd
from pathlib import Path


def load(path: Path) -> pd.DataFrame:

    conn = sqlite3.connect(path)
    df = pd.read_sql_query("SELECT * FROM vacancies", conn)
    conn.close()

    return df


def save(df: pd.DataFrame, path: Path):

    conn = sqlite3.connect(path)
    df.to_sql("vacancies", conn, if_exists="replace", index=False)
    conn.close()
