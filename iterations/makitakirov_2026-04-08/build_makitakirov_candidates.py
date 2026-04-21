from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "work" / "tools_without_images.xlsx"
OUTPUT_FILE = BASE_DIR / "work" / "makitakirov_candidates.xlsx"

COL_ARTICLE = "Артикул [ARTIKUL]"
COL_NAME = "Наименование элемента"

SOURCE_NAME = "makitakirov.rf"
SOURCE_BASE_URL = "https://xn--80aagwbjclyts.xn--p1ai"


def is_empty(value) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def build_search_url(article: str) -> str:
    return f"{SOURCE_BASE_URL}/search?q={quote_plus(article)}"


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Filtered file not found: {INPUT_FILE}")

    df = pd.read_excel(INPUT_FILE)

    required_columns = [COL_ARTICLE, COL_NAME]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    work_df = df.copy()
    work_df["_article"] = work_df[COL_ARTICLE].fillna("").astype(str).str.strip()
    work_df = work_df[~work_df["_article"].apply(is_empty)].copy()

    work_df["source_name"] = SOURCE_NAME
    work_df["search_url"] = work_df["_article"].apply(build_search_url)
    work_df["product_url"] = ""
    work_df["status"] = "new"
    work_df["note"] = ""

    output_columns = [
        COL_ARTICLE,
        COL_NAME,
        "source_name",
        "search_url",
        "product_url",
        "status",
        "note",
    ]
    result = work_df[output_columns].copy()
    result.to_excel(OUTPUT_FILE, index=False)

    print("\n=== CANDIDATE FILE READY ===")
    print(f"Input rows: {len(df)}")
    print(f"Candidate rows: {len(result)}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
