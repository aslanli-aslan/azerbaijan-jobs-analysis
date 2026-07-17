from jobanalysis.paths import FINAL_DATA
from jobanalysis.io import load


def tableau_ready_format():
    df = load(FINAL_DATA)

    vacancies_df = df.drop(columns=["required_languages", "description"])
    
    languages_df = df[["id", "required_languages"]]

    languages_df["required_languages"] = languages_df["required_languages"].str.split(",")
    languages_df = languages_df.explode("required_languages")

    languages_df["required_languages"] = languages_df["required_languages"].str.strip()


    vacancies_df.to_csv(FINAL_DATA.parent / "vacancies.csv", index=False)
    languages_df.to_csv(FINAL_DATA.parent / "languages.csv", index=False)


if __name__ == "__main__":
    tableau_ready_format()