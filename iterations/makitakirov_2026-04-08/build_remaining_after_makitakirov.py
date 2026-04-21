from pathlib import Path
import re

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
FILTERED_FILE = BASE_DIR / "work" / "tools_without_images.xlsx"
REPORT_FILE = BASE_DIR / "output" / "makitakirov_report.xlsx"
OUTPUT_FILE = BASE_DIR / "output" / "remaining_after_makitakirov.xlsx"
OUTPUT_WITH_ARTICLE_FILE = BASE_DIR / "output" / "remaining_with_article_only.xlsx"

COL_ARTICLE = "Артикул [ARTIKUL]"
COL_STATUS = "status"


def normalize_article(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().upper()
    text = re.sub(r"\s+", "", text)
    return text


def main():
    if not FILTERED_FILE.exists():
        raise FileNotFoundError(f"Filtered file not found: {FILTERED_FILE}")
    if not REPORT_FILE.exists():
        raise FileNotFoundError(f"Report file not found: {REPORT_FILE}")

    filtered_df = pd.read_excel(FILTERED_FILE)
    report_df = pd.read_excel(REPORT_FILE)

    if COL_ARTICLE not in filtered_df.columns:
        raise ValueError(f"Missing column in filtered file: {COL_ARTICLE}")
    if "article" not in report_df.columns:
        raise ValueError("Missing column in report file: article")
    if COL_STATUS not in report_df.columns:
        raise ValueError(f"Missing column in report file: {COL_STATUS}")

    ok_articles = set(
        report_df.loc[report_df[COL_STATUS] == "OK", "article"]
        .map(normalize_article)
        .tolist()
    )

    work_df = filtered_df.copy()
    work_df["_article_norm"] = work_df[COL_ARTICLE].map(normalize_article)

    remaining_df = work_df[~work_df["_article_norm"].isin(ok_articles)].copy()
    remaining_df = remaining_df.drop(columns=["_article_norm"], errors="ignore")
    remaining_df.reset_index(drop=True, inplace=True)

    remaining_with_article_df = remaining_df[
        remaining_df[COL_ARTICLE].map(normalize_article) != ""
    ].copy()
    remaining_with_article_df.reset_index(drop=True, inplace=True)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    remaining_df.to_excel(OUTPUT_FILE, index=False)
    remaining_with_article_df.to_excel(OUTPUT_WITH_ARTICLE_FILE, index=False)

    print("\n=== REMAINING ITEMS SUMMARY ===")
    print(f"Filtered input rows: {len(filtered_df)}")
    print(f"Successful items in report: {len(ok_articles)}")
    print(f"Remaining rows: {len(remaining_df)}")
    print(f"Remaining rows with article: {len(remaining_with_article_df)}")
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"Saved to: {OUTPUT_WITH_ARTICLE_FILE}")


if __name__ == "__main__":
    main()
