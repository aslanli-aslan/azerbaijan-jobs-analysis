import pandas as pd
import re
import unicodedata


def extract_experience(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    EXPERIENCE_PATTERN_FORWARD = r"(?:(?:(\d+)[\d \t\xa0.,\-–+]*)(?:\(\w+\)\s*)?(?:il\w*|year\w*|лет|год\w*|летним))\b.*?(?:təcrübə|experience|опыт|staj)"
    EXPERIENCE_PATTERN_BACKWARD = r"(?:təcrübə\w*|staj\w*|experience|опыт)[\w \t\xa0:,(/)\-–]*?(?:ən\s+az\w*|от|min\.?\s*)?(?:(\d+)[\d \t\xa0.,\-–+\w]*(?:\(\w+\)\s*)?(?:il\w*|year\w*|лет|год\w*)\b)(?!\s*(?:AZN|azn|manat|₼|руб|USD|\$))"

    MONTH_PATTERN_FORWARD = r"(?:(?:(\d+)[\d \t\xa0.,\-–+]*)(?:\(\w+\)\s*)?(?:ay\w*|month\w*|мес\w*))\b.*?(?:təcrübə|experience|опыт|staj)"
    MONTH_PATTERN_BACKWARD = r"(?:təcrübə\w*|staj\w*|experience|опыт)[\w \t\xa0:,(/)\-–]*?(?:ən\s+az\w*|от|min\.?\s*)?(?:(\d+)[\d \t\xa0.,\-–+\w]*(?:\(\w+\)\s*)?(?:ay\w*|month\w*|мес\w*)\b)(?!\s*(?:AZN|azn|manat|₼|руб|USD|\$))"

    NO_EXP_PATTERN = r"(təcrübəsiz|no experience|experience not required|опыт не требуется|təcrübə tələb olunmur)"

    def _extract_experience_from_description(text):
        text = unicodedata.normalize("NFC", text)

        m = re.findall(EXPERIENCE_PATTERN_FORWARD, text, re.IGNORECASE)
        if m:
            return min([int(x) for x in m])
        m = re.findall(EXPERIENCE_PATTERN_BACKWARD, text, re.IGNORECASE)
        if m:
            return min([int(x) for x in m])

        m = re.findall(MONTH_PATTERN_FORWARD, text, re.IGNORECASE)
        if m:
            return min([int(x) for x in m]) / 12.0
        m = re.findall(MONTH_PATTERN_BACKWARD, text, re.IGNORECASE)
        if m:
            return min([int(x) for x in m]) / 12.0

        if re.findall(NO_EXP_PATTERN, text, re.IGNORECASE):
            return 0.0
        return None

    df["experience_years_min"] = df["description"].apply(
        _extract_experience_from_description
    )

    df.loc[df["experience_years_min"] > 15, "experience_years_min"] = None

    return df


def extract_education(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    PATTERNS = {
        "Not Required": (
            r"təhsil\s+tələb\s+olunmur|təhsil[iə]?\s+vacib\s+deyil|təhsil[iə]?\s+fərq[iə]\s+yoxdur|xüsusi\s+təhsil\s+tələb\s+olunmur|"
            r"təhsil\s*:\s*(?:vacib\s+deyil|tələb\s+olunmur|fərq\s+etmir|fərqi\s+yoxdur)|"
            r"без\s+требований\s+к\s+образованию|образование\s+не\s+важно|образование\s+не\s+требуется|"
            r"education\s+is\s+not\s+required|no\s+education\s+required"
        ),
        "Middle": (
            r"(\borta\b[\w \t\xa0.,:\-–\/\(\)\\]{0,50}?\btəhsil\w*|"
            r"\btəhsil\w*[\w \t\xa0.,:\-–\/\(\)\\]{0,50}?\borta\b|"
            r"\bсреднн?[еи]е\b[\w \t\xa0.,:\-–\/\(\)\\]{0,15}?\bобразовани\w*|"
            r"\bобразовани\w*\b[\w \t\xa0.,:\-–\/\(\)\\]{0,15}?\bсреднн?[еи]е\b|"
            r"\bpeşə\b[\w \t\xa0.,:\-–\/\(\)\\]{0,50}?\btəhsil\w*|"
            r"(?<!ali\s)(?<!higher\s)\btexniki\b[\w \t\xa0.,:\-–\/\(\)\\]{0,50}?\btəhsil\w*|"
            r"\b(orta\s+ixtisas|orta-ixtisas|college\s+(?:diploma|degree|education)|secondary\s+education(?:\s+(?:diploma|certificate|required|completed))?|secondary\s+school|high\s+school\s+(?:diploma|education|graduate|certificate)|peşə\s+məktəb\w*|vocational\s+(?:education|school|training)|(?<!higher\s)(?<!ali\s)technical\s+education|средне-специальное|средне\.?специальное|средне-техническое|среднн?ее\s+специальное|среднее\s+профессиональное)\b)"
        ),
        "Bachelor": (
            r"(\bali\b[\w \t\xa0.,:\-–\/\(\)\\]{0,50}?\btəhsil\w*|"
            r"\btəhsil\w*[\w \t\xa0.,:\-–\/\(\)\\]{0,50}?\bali\b|"
            r"\b(bakalavr\w*|bakalavriat\w*|бакалавр\w*|бакалавриат\w*|bachelor'?s?|b\.s\b|b\.a\b|undergraduate|higher\s+education|university\s+degree|degree\s*in|degree\s+(?:or\s+certification\s+)?in|high\s+education|higher\s+technical\s+education|высшее\s+образование|высш(?:ее|его|ему|им|е|e)|(?:bs|ba|b\.s|b\.a)\s+degree|degree\s+qualified)\b)"
        ),
        "Master": r"\b(magistr\w*|magistratura\w*|магистр\w*|магистратура\w*|master'?s?\s+degree|master's\b|masters\b|mba|ph\.?d|(?:ms|ma|m\.s|m\.a)\s+degree)\b",
    }

    FALLBACK_PATTERNS = {
        "Bachelor": (
            r"\b(sahə|tibb|müvafiq|üzrə)[\w \t\xa0.,:\-–\/\(\)\\]{0,50}?\btəhsil\w*"
        ),
        "Middle": (r"\b(diplom(?:u|ı|a|ın|lar|lu)?|diploma)\b"),
    }

    def _extract_education_from_description(text):
        for level, pattern in PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                return level

        for level, pattern in FALLBACK_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                return level

        return "Not Mentioned"

    df["education_level_min"] = df["description"].apply(
        _extract_education_from_description
    )
    return df
