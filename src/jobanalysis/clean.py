import pandas as pd
from jobanalysis.paths import RAW_DATA, PROCESSED_DATA
from jobanalysis.io import load, save

def parse_salary(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["salary"] = df["salary"].astype(int)
    df["salary"] = df["salary"].replace(0, float("nan"))

    return df

def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["created_at"] = pd.to_datetime(df["created_at"])
    df["deadline_at"] = pd.to_datetime(df["deadline_at"])
    df = df.dropna(subset="deadline_at")

    return df

def parse_company(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["company"] = df["company"].replace("Company", None)

    return df

def parse_view_count(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["view_count"] = df["view_count"].apply(lambda x: int(float(x[:-1]) * 1000) if (isinstance(x, str) and 'K' in x) else x)

    return df

def clean(save_output: bool = True) -> pd.DataFrame:
    df = load(RAW_DATA)
    df = parse_salary(df)
    df = parse_dates(df)
    df = parse_company(df)
    df = parse_view_count(df)
    df = df.drop(columns=["id", "company_id", "url", "fetched_at", "direct_apply"])

    if save_output:
        save(df, PROCESSED_DATA)

    return df

if __name__ == "__main__":
    clean()

