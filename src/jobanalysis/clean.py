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

    df["view_count"] = df["view_count"].apply(
        lambda x: int(float(x[:-1]) * 1000) if (isinstance(x, str) and "K" in x) else x
    )

    return df


def normalize_category(df: pd.DataFrame) -> pd.DataFrame:
    _category_groups = {
        "Inzibati, Biznes və İdarəetmə": "Inzibati, Biznes və İdarəetmə",
        "Biznes, İdarəetmə və İnsan Resursları": "Inzibati, Biznes və İdarəetmə",
        "Biznesin İnkişafı": "Inzibati, Biznes və İdarəetmə",
        "Layihə və Proqram İdarəetməsi": "Inzibati, Biznes və İdarəetmə",
        "Ofis İnzibatçılığı": "Inzibati, Biznes və İdarəetmə",
        "Əməliyyatların İdarə Edilməsi": "Inzibati, Biznes və İdarəetmə",
        "Maliyyə xidmətləri": "Maliyyə xidmətləri",
        "Maliyyə, Bankçılıq və Sığorta": "Maliyyə xidmətləri",
        "Bank Əməliyyatları": "Maliyyə xidmətləri",
        "Audit və Vergi": "Maliyyə xidmətləri",
        "Mühəndislik": "Mühəndislik",
        "Mühəndislik və Texniki Sahələr": "Mühəndislik",
        "Maşınqayırma (Mexanika) Mühəndisliyi": "Mühəndislik",
        "Elektrik, Elektronika və Avtomatlaşdırma": "Mühəndislik",
        "Mühəndislik Dəstəyi": "Mühəndislik",
        "Mülki və Tikinti Mühəndisliyi": "Mühəndislik",
        "Pərakəndə satış və müştəri xidmətləri": "Pərakəndə satış və müştəri xidmətləri",
        "Satış, Pərakəndə və Müştəri Xidmətləri": "Pərakəndə satış və müştəri xidmətləri",
        "Müştəri Xidmətləri": "Pərakəndə satış və müştəri xidmətləri",
        "Pərakəndə Satış": "Pərakəndə satış və müştəri xidmətləri",
        "Satış İdarəetməsi": "Pərakəndə satış və müştəri xidmətləri",
        "Komputerləşmə və İKT": "Komputerləşmə və İKT",
        "İT, Proqram Təminatı və Məlumat Analitikası": "Komputerləşmə və İKT",
        "Məlumat Analitikası": "Komputerləşmə və İKT",
        "Marketinq, reklam, çap və nəşriyyat": "Marketinq, reklam, çap və nəşriyyat",
        "Marketinq, Media və Kommunikasiyalar": "Marketinq, reklam, çap və nəşriyyat",
        "Dizayn, incəsənət və sənətkarlıq": "Marketinq, reklam, çap və nəşriyyat",
        "Dizayn, Yaradıcılıq və Media": "Marketinq, reklam, çap və nəşriyyat",
        "İfaçılıq sənəti və media": "Marketinq, reklam, çap və nəşriyyat",
        "Media istehsalı (prodakşn)": "Marketinq, reklam, çap və nəşriyyat",
        "Nəqliyyat, paylama və logistika": "Nəqliyyat, paylama və logistika",
        "Logistika və Nəqliyyat": "Nəqliyyat, paylama və logistika",
        "Anbar Əməliyyatları": "Nəqliyyat, paylama və logistika",
        "Sürücülük": "Nəqliyyat, paylama və logistika",
        "Satınalma və Təchizat Zənciri": "Nəqliyyat, paylama və logistika",
        "Satınalma və Tədarük": "Nəqliyyat, paylama və logistika",
        "Otel, İaşə, Turizm": "Otel, İaşə, Turizm",
        "Otel, İaşə və Turizm": "Otel, İaşə, Turizm",
        "İaşə və Qida Xidmətləri": "Otel, İaşə, Turizm",
        "Təlim və tədris": "Təhsil və Təlim",
        "Təhsil və Təlim": "Təhsil və Təlim",
        "Korporativ Təlim": "Təhsil və Təlim",
        "Dillər": "Təhsil və Təlim",
        "İnşaat və tikinti": "Tikinti, Memarlıq və Əmlak",
        "Memarlıq": "Tikinti, Memarlıq və Əmlak",
        "Memarlıq və Memarlığın İdarə Edilməsi": "Tikinti, Memarlıq və Əmlak",
        "Təsərrüfat və əmlak xidmətləri": "Tikinti, Memarlıq və Əmlak",
        "Əmlak və Təsərrüfat İdarəçiliyi": "Tikinti, Memarlıq və Əmlak",
        "Hüquq və məhkəmə xidmətləri": "Hüquq və Uyğunluq",
        "Hüquq və Uyğunluq (Compliance)": "Hüquq və Uyğunluq",
        "İstehsalat": "İstehsalat",
        "İstehsalat və İstehsal": "İstehsalat",
        "İxtisaslı Fəhlə və Texniki Peşələr": "İstehsalat",
        "Səhiyyə": "Səhiyyə",
        "Səhiyyə və Əczaçılıq": "Səhiyyə",
        "Digər Tibb Mütəxəssisləri": "Səhiyyə",
        "Təhlükəsizlik, uniforma və qoruyucu xidmətlər": "Təhlükəsizlik və Mühafizə",
        "Təhlükəsizlik və Mühafizə Xidmətləri": "Təhlükəsizlik və Mühafizə",
        "Təmizlik Xidmətləri": "Təmizlik Xidmətləri",
        "Ümumi Fəhlə və Başlanğıc Səviyyəli İşlər": "Ümumi Fəhlə İşləri",
        "Ümumi Fəhlə İşləri": "Ümumi Fəhlə İşləri",
        "Köməkçi İşçilər": "Ümumi Fəhlə İşləri",
        "Kənd Təsərrüfatı və Ətraf Mühit Xidmətləri": "Kənd Təsərrüfatı və Ətraf Mühit",
        "Heyvandarlıq və Baytarlıq": "Kənd Təsərrüfatı və Ətraf Mühit",
        "Ətraf Mühit və Əməyin Mühafizəsi": "Kənd Təsərrüfatı və Ətraf Mühit",
    }

    df["category"] = df["category"].map(_category_groups)

    return df


def clean(save_output: bool = True) -> pd.DataFrame:
    df = load(RAW_DATA)
    df = parse_salary(df)
    df = parse_dates(df)
    df = parse_company(df)
    df = parse_view_count(df)
    df = normalize_category(df)
    df = df.drop(columns=["id", "company_id", "url", "fetched_at", "direct_apply"])

    if save_output:
        save(df, PROCESSED_DATA)

    return df


if __name__ == "__main__":
    clean()
