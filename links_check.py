import pandas as pd

# =========================
# НАСТРОЙКИ
# =========================
RESULT_FILE = "tools_without_images.xlsx"      # файл после твоего фильтра
SOURCE_FILE = "source_with_links.xlsx"         # файл, где есть "Модель/Артикул" и "Карточка товара"

RESULT_SHEET = 0
SOURCE_SHEET = 0

OUTPUT_MATCHED = "matched_with_links.xlsx"
OUTPUT_UNMATCHED = "unmatched_articles.xlsx"

# Колонки в файле результата
RESULT_ARTICLE_COL = "Артикул [ARTIKUL]"
RESULT_NAME_COL = "Наименование элемента"

# Колонки во втором файле
SOURCE_ARTICLE_COL = "Модель/Артикул"
SOURCE_LINK_COL = "Карточка товара"

# =========================
# УТИЛИТЫ
# =========================
def normalize_article(value) -> str:
    """
    Приводим артикул к строке:
    - trim
    - upper
    - убираем пробелы по краям
    """
    if pd.isna(value):
        return ""
    return str(value).strip().upper()

def is_empty(value) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""

# =========================
# ОСНОВНАЯ ЛОГИКА
# =========================
def main():
    result_df = pd.read_excel(RESULT_FILE, sheet_name=RESULT_SHEET)
    source_df = pd.read_excel(SOURCE_FILE, sheet_name=SOURCE_SHEET)

    # Проверка колонок
    required_result_cols = [RESULT_ARTICLE_COL, RESULT_NAME_COL]
    required_source_cols = [SOURCE_ARTICLE_COL, SOURCE_LINK_COL]

    missing_result = [col for col in required_result_cols if col not in result_df.columns]
    missing_source = [col for col in required_source_cols if col not in source_df.columns]

    if missing_result:
        raise ValueError(f"В RESULT_FILE нет колонок: {missing_result}")

    if missing_source:
        raise ValueError(f"В SOURCE_FILE нет колонок: {missing_source}")

    # Нормализация артикулов
    result_df = result_df.copy()
    source_df = source_df.copy()

    result_df["_article_norm"] = result_df[RESULT_ARTICLE_COL].apply(normalize_article)
    source_df["_article_norm"] = source_df[SOURCE_ARTICLE_COL].apply(normalize_article)

    # Убираем пустые артикулы из source, чтобы не было мусора
    source_df = source_df[source_df["_article_norm"] != ""].copy()

    # На случай дублей по артикулу в source:
    # оставляем первую непустую ссылку
    source_df["_link_not_empty"] = ~source_df[SOURCE_LINK_COL].apply(is_empty)
    source_df = source_df.sort_values(
        by=["_article_norm", "_link_not_empty"],
        ascending=[True, False]
    )
    source_unique = source_df.drop_duplicates(subset=["_article_norm"], keep="first").copy()

    # Джойним
    merged = result_df.merge(
        source_unique[["_article_norm", SOURCE_ARTICLE_COL, SOURCE_LINK_COL]],
        on="_article_norm",
        how="left",
        suffixes=("", "_source")
    )

    # Что совпало и где ссылка есть
    matched_df = merged[~merged[SOURCE_LINK_COL].apply(is_empty)].copy()

    # Что не совпало вообще или совпало, но ссылки нет
    unmatched_df = merged[merged[SOURCE_LINK_COL].apply(is_empty)].copy()

    # Переименуем для читаемости
    matched_df = matched_df.rename(columns={
        SOURCE_ARTICLE_COL: "Артикул из source",
        SOURCE_LINK_COL: "Ссылка на карточку"
    })

    unmatched_df = unmatched_df.rename(columns={
        SOURCE_ARTICLE_COL: "Артикул из source",
        SOURCE_LINK_COL: "Ссылка на карточку"
    })

    # Сохраняем
    matched_df.drop(columns=["_article_norm"], errors="ignore").to_excel(OUTPUT_MATCHED, index=False)
    unmatched_df.drop(columns=["_article_norm"], errors="ignore").to_excel(OUTPUT_UNMATCHED, index=False)

    # Логи
    total_result = len(result_df)
    total_source = len(source_df)
    total_source_unique = len(source_unique)
    total_matched = len(matched_df)
    total_unmatched = len(unmatched_df)

    print("\n=== СВЕРКА ПО АРТИКУЛАМ ===")
    print(f"Строк в результате фильтрации: {total_result}")
    print(f"Строк во втором файле: {total_source}")
    print(f"Уникальных артикулов во втором файле: {total_source_unique}")
    print(f"Совпало и есть ссылка: {total_matched}")
    print(f"Не найдено / нет ссылки: {total_unmatched}")
    print(f"\nСохранено:")
    print(f"- Совпадения: {OUTPUT_MATCHED}")
    print(f"- Без совпадений: {OUTPUT_UNMATCHED}")

if __name__ == "__main__":
    main()