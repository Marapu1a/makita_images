from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "pictures.xlsx"
OUTPUT_FILE = BASE_DIR / "elitech_and_teh_without_images.xlsx"

MAIN_SECTION_COL = "Название основного раздела"
ARTICLE_COL = "Артикул [ARTIKUL]"
PREVIEW_COL = "Картинка для анонса (путь)"
MORE_PHOTO_COL = "Картинки галереи [MORE_PHOTO]"
TARGET_SECTIONS = {"Elitech", "TEH"}


def is_empty(value: object) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    df = pd.read_excel(INPUT_FILE)

    required_columns = [MAIN_SECTION_COL, ARTICLE_COL, PREVIEW_COL, MORE_PHOTO_COL]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    work_df = df.copy()

    section_mask = work_df[MAIN_SECTION_COL].fillna("").astype(str).str.strip().isin(TARGET_SECTIONS)
    preview_empty_mask = work_df[PREVIEW_COL].map(is_empty)
    gallery_empty_mask = work_df[MORE_PHOTO_COL].map(is_empty)
    article_present_mask = work_df[ARTICLE_COL].fillna("").astype(str).str.strip() != ""

    filtered_df = work_df[
        section_mask & preview_empty_mask & gallery_empty_mask & article_present_mask
    ].copy()
    filtered_df.reset_index(drop=True, inplace=True)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    filtered_df.to_excel(OUTPUT_FILE, index=False)

    print("\n=== ELITECH_AND_TEH FILTER SUMMARY ===")
    print(f"Input rows: {len(df)}")
    print(f"Rows in target main sections {sorted(TARGET_SECTIONS)}: {int(section_mask.sum())}")
    print(f"Rows with empty preview and gallery plus article: {len(filtered_df)}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
