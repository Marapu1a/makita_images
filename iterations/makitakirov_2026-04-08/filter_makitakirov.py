from pathlib import Path
import re

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "input" / "pictures.xlsx"
OUTPUT_FILE = BASE_DIR / "work" / "tools_without_images.xlsx"
SHEET_NAME = 0

COL_ARTICLE = "Артикул [ARTIKUL]"
COL_NAME = "Наименование элемента"
COL_PARENT = "Название раздела"
COL_SECTION = "Название раздела.1"
COL_GALLERY = "Картинки галереи [MORE_PHOTO]"
COL_PREVIEW = "Картинка для анонса (путь)"

PARENT_CATEGORY_PATTERNS = {
    "DeWalt": [r"\bdewalt\b"],
    "Milwaukee": [r"\bmilwaukee\b"],
    "Elitech": [r"\belitech\b"],
    "TEH": [r"\bteh\b"],
    "INGCO": [r"\bingco\b"],
    "Spare parts": [r"запасн"],
    "Accessories": [r"аксессуар", r"расходн"],
}

SECTION_CATEGORY_PATTERNS = {
    "Spare parts": [
        r"запчаст",
        r"прочие запчаст",
        r"заглушк",
        r"кольц",
        r"рычаг",
        r"крышк",
        r"контактн",
        r"блоки",
        r"разъем",
        r"схем",
        r"шкив",
        r"штекер",
        r"двигател",
        r"статор",
        r"ротор",
        r"якор",
        r"щетк",
        r"патрон",
        r"чашка сцепления",
    ],
    "Accessories": [
        r"боковые рукоятки",
        r"рукоятк",
        r"насад",
        r"диски",
        r"пилки",
        r"сверл",
        r"буры",
        r"коронк",
        r"оснаст",
        r"аккумулятор",
        r"зарядн",
    ],
    "Non-tool": [
        r"коробк",
    ],
}


def is_empty(value) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def normalize(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def matches_any_pattern(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def get_matched_categories(text: str, category_patterns: dict[str, list[str]]) -> list[str]:
    matched = []
    for category, patterns in category_patterns.items():
        if matches_any_pattern(text, patterns):
            matched.append(category)
    return matched


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)

    required_columns = [COL_ARTICLE, COL_NAME, COL_PARENT, COL_SECTION, COL_GALLERY, COL_PREVIEW]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    no_images_mask = df[COL_GALLERY].apply(is_empty) & df[COL_PREVIEW].apply(is_empty)
    no_images_df = df[no_images_mask].copy()

    no_section_mask = no_images_df[COL_PARENT].apply(is_empty) & no_images_df[COL_SECTION].apply(is_empty)

    parent_text = no_images_df[COL_PARENT].apply(normalize)
    section_text = no_images_df[COL_SECTION].apply(normalize)

    bad_parent_mask = parent_text.apply(
        lambda value: len(get_matched_categories(value, PARENT_CATEGORY_PATTERNS)) > 0
    )
    bad_section_mask = section_text.apply(
        lambda value: len(get_matched_categories(value, SECTION_CATEGORY_PATTERNS)) > 0
    )

    result = no_images_df[(~no_section_mask) & (~bad_parent_mask) & (~bad_section_mask)].copy()
    result.reset_index(drop=True, inplace=True)
    result.to_excel(OUTPUT_FILE, index=False)

    print("\n=== FILTER SUMMARY ===")
    print(f"Input rows: {len(df)}")
    print(f"Rows without images: {len(no_images_df)}")
    print(f"Rows without section info: {int(no_section_mask.sum())}")
    print(f"Rows after filtering: {len(result)}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
