from __future__ import annotations

from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "input" / "pictures.xlsx"
OUTPUT_DIR = BASE_DIR / "output" / "import_images"
OUTPUT_FILE = BASE_DIR / "output" / "remaining_after_mtools_be.xlsx"

COL_ARTICLE = "Артикул [ARTIKUL]"


def normalize_article(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().upper()


def main() -> None:
    df = pd.read_excel(INPUT_FILE)
    df[COL_ARTICLE] = df[COL_ARTICLE].map(normalize_article)
    df = df[df[COL_ARTICLE].astype(bool)].copy()

    existing: set[str] = set()
    if OUTPUT_DIR.exists():
        for folder in OUTPUT_DIR.iterdir():
            if folder.is_dir() and (folder / "preview.webp").exists():
                existing.add(normalize_article(folder.name))

    remaining = df[~df[COL_ARTICLE].isin(existing)].copy()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    remaining.to_excel(OUTPUT_FILE, index=False)

    print(f"existing={len(existing)} remaining={len(remaining)}")


if __name__ == "__main__":
    main()
