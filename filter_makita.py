import pandas as pd
import re

INPUT_FILE = "pictures.xlsx"
SHEET_NAME = 0
OUTPUT_FILE = "tools_without_images.xlsx"

COL_PARENT = "Название родительского раздела"
COL_SECTION = "Название раздела"
COL_GALLERY = "Картинки галереи [MORE_PHOTO]"
COL_PREVIEW = "Картинка для анонса (путь)"

# Категории для статистики и фильтрации по родительскому разделу
PARENT_CATEGORY_PATTERNS = {
    "DeWalt": [r"\bdewalt\b"],
    "Milwaukee": [r"\bmilwaukee\b"],
    "Elitech": [r"\belitech\b"],
    "TEH": [r"\bteh\b"],
    "INGCO": [r"\bingco\b"],
    "Запчасти": [r"запасн"],
    "Аксессуары / расходка": [r"аксессуар", r"расходн"],
}

# Категории для статистики и фильтрации по разделу
SECTION_CATEGORY_PATTERNS = {
    "Запчасти": [
        r"запчаст",
        r"прочие запчаст",
        r"заглушк",
        r"кольца",
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
    "Аксессуары / расходка": [
        r"боковые рукоятки",
        r"рукоятки",
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
    "Прочее не-инструмент": [
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
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)

    required_columns = [COL_PARENT, COL_SECTION, COL_GALLERY, COL_PREVIEW]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"В файле нет нужных колонок: {missing_columns}")

    # 1. Только товары, у которых пусто и в галерее, и в анонсе
    no_images_mask = (
        df[COL_GALLERY].apply(is_empty) &
        df[COL_PREVIEW].apply(is_empty)
    )
    no_images_df = df[no_images_mask].copy()

    # 2. Строки без привязки к разделу вообще
    no_section_mask = (
        no_images_df[COL_PARENT].apply(is_empty) &
        no_images_df[COL_SECTION].apply(is_empty)
    )

    # 3. Нормализованные тексты
    parent_text = no_images_df[COL_PARENT].apply(normalize)
    section_text = no_images_df[COL_SECTION].apply(normalize)

    # 4. Подробная статистика
    parent_stats = {}
    for category, patterns in PARENT_CATEGORY_PATTERNS.items():
        count = parent_text.apply(lambda x: matches_any_pattern(x, patterns)).sum()
        parent_stats[category] = int(count)

    section_stats = {}
    for category, patterns in SECTION_CATEGORY_PATTERNS.items():
        count = section_text.apply(lambda x: matches_any_pattern(x, patterns)).sum()
        section_stats[category] = int(count)

    # 5. Общие маски для выкидывания
    bad_parent_mask = parent_text.apply(
        lambda x: len(get_matched_categories(x, PARENT_CATEGORY_PATTERNS)) > 0
    )
    bad_section_mask = section_text.apply(
        lambda x: len(get_matched_categories(x, SECTION_CATEGORY_PATTERNS)) > 0
    )

    # 6. Финальный отбор
    result = no_images_df[
        (~no_section_mask) &
        (~bad_parent_mask) &
        (~bad_section_mask)
    ].copy()

    result.reset_index(drop=True, inplace=True)
    result.to_excel(OUTPUT_FILE, index=False)

    # 7. Красивый лог
    print("\n=== СТАТИСТИКА ПО ТОВАРАМ БЕЗ КАРТИНОК ===")
    print(f"Всего строк в исходнике: {len(df)}")
    print(f"Всего товаров без картинок: {len(no_images_df)}")
    print(f"Без привязки к разделу: {int(no_section_mask.sum())}")

    print("\n--- По родительским разделам ---")
    for category, count in parent_stats.items():
        print(f"{category}: {count}")
    
    print("\n--- (некоторые строки могут попадать в несколько категорий)")

    print("\n--- Финал ---")
    print(f"Останется кандидатов после фильтрации: {len(result)}")
    print(f"Результат сохранён в: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()