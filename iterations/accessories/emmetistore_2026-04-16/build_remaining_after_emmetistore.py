from __future__ import annotations

from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "input" / "pictures.xlsx"
IMAGES_DIR = BASE_DIR / "output" / "import_images"
OUTPUT_FILE = BASE_DIR / "output" / "remaining_after_emmetistore.xlsx"

COL_ARTICLE = "Артикул [ARTIKUL]"


def normalize_article(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().upper()


def collect_confirmed_articles() -> set[str]:
    confirmed: set[str] = set()
    if not IMAGES_DIR.exists():
        return confirmed

    for folder in IMAGES_DIR.iterdir():
        if not folder.is_dir():
            continue
        if not (folder / "preview.webp").exists():
            continue
        confirmed.add(normalize_article(folder.name))
    return confirmed


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    df = pd.read_excel(INPUT_FILE)
    if COL_ARTICLE not in df.columns:
        raise ValueError(f"Missing required column: {COL_ARTICLE}")

    confirmed = collect_confirmed_articles()
    remaining = df[~df[COL_ARTICLE].map(normalize_article).isin(confirmed)].copy()
    remaining.to_excel(OUTPUT_FILE, index=False)

    print(f"Input rows: {len(df)}")
    print(f"Confirmed folders: {len(confirmed)}")
    print(f"Remaining rows: {len(remaining)}")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
