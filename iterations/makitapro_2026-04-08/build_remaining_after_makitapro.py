from pathlib import Path
import re

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "input" / "pictures.xlsx"
REPORT_FILE = BASE_DIR / "output" / "makitapro_report.xlsx"
OUTPUT_FILE = BASE_DIR / "output" / "remaining_after_makitapro.xlsx"

COL_ARTICLE = "Артикул [ARTIKUL]"
COL_STATUS = "status"


def normalize_article(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().upper()
    return re.sub(r"\s+", "", text)


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")
    if not REPORT_FILE.exists():
        raise FileNotFoundError(f"Report file not found: {REPORT_FILE}")

    input_df = pd.read_excel(INPUT_FILE)
    report_df = pd.read_excel(REPORT_FILE)

    if COL_ARTICLE not in input_df.columns:
        raise ValueError(f"Missing column in input file: {COL_ARTICLE}")
    if "article" not in report_df.columns:
        raise ValueError("Missing column in report file: article")
    if COL_STATUS not in report_df.columns:
        raise ValueError(f"Missing column in report file: {COL_STATUS}")

    ok_articles = set(
        report_df.loc[report_df[COL_STATUS] == "OK", "article"]
        .map(normalize_article)
        .tolist()
    )

    work_df = input_df.copy()
    work_df["_article_norm"] = work_df[COL_ARTICLE].map(normalize_article)

    remaining_df = work_df[~work_df["_article_norm"].isin(ok_articles)].copy()
    remaining_df = remaining_df.drop(columns=["_article_norm"], errors="ignore")
    remaining_df.reset_index(drop=True, inplace=True)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    remaining_df.to_excel(OUTPUT_FILE, index=False)

    print("\n=== REMAINING AFTER MAKITAPRO ===")
    print(f"Input rows: {len(input_df)}")
    print(f"Successful items in report: {len(ok_articles)}")
    print(f"Remaining rows: {len(remaining_df)}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
