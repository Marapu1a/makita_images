from pathlib import Path
import re

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "input" / "pictures.xlsx"
IMAGES_DIR = BASE_DIR / "output" / "import_images"
OUTPUT_FILE = BASE_DIR / "output" / "remaining_after_makitasparesm.xlsx"


def normalize_article(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().upper()
    return re.sub(r"\s+", "", text)


def find_article_column(columns: list[str]) -> str:
    for column in columns:
        if "ARTIKUL" in str(column).upper():
            return column
    raise ValueError("Could not find article column in input file")


def get_confirmed_articles(images_dir: Path) -> set[str]:
    confirmed_articles: set[str] = set()

    if not images_dir.exists():
        return confirmed_articles

    for folder in images_dir.iterdir():
        if not folder.is_dir():
            continue
        if (folder / "preview.webp").exists():
            confirmed_articles.add(normalize_article(folder.name))

    return confirmed_articles


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")
    if not IMAGES_DIR.exists():
        raise FileNotFoundError(f"Images directory not found: {IMAGES_DIR}")

    input_df = pd.read_excel(INPUT_FILE)
    article_col = find_article_column(input_df.columns.tolist())
    confirmed_articles = get_confirmed_articles(IMAGES_DIR)

    work_df = input_df.copy()
    work_df["_article_norm"] = work_df[article_col].map(normalize_article)

    remaining_df = work_df[~work_df["_article_norm"].isin(confirmed_articles)].copy()
    remaining_df = remaining_df.drop(columns=["_article_norm"], errors="ignore")
    remaining_df.reset_index(drop=True, inplace=True)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    remaining_df.to_excel(OUTPUT_FILE, index=False)

    print("\n=== REMAINING AFTER MAKITASPARESM ===")
    print(f"Input rows: {len(input_df)}")
    print(f"Confirmed product folders: {len(confirmed_articles)}")
    print(f"Remaining rows: {len(remaining_df)}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
