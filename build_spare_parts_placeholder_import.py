from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_XLSX = BASE_DIR / "export_btx.xlsx"
OUTPUT_XLSX = BASE_DIR / "spare_parts_placeholder_import_2026-05-10.xlsx"

COL_ARTICLE = "Артикул [ARTIKUL]"
COL_SECTION = "Название раздела"
COL_IMAGE = "Картинка для анонса (путь)"
SPARE_SECTION = "Запасные части"
PLACEHOLDER_PATH = "/upload/vvm_images/import_images/placeholder.webp"


def is_empty_image(value: object) -> bool:
    if pd.isna(value):
        return True
    text = str(value).strip()
    return text == "" or text.lower() == "nan"


def main() -> None:
    df = pd.read_excel(INPUT_XLSX)

    spare_mask = df[COL_SECTION].astype(str).str.strip().eq(SPARE_SECTION)
    empty_mask = df[COL_IMAGE].map(is_empty_image)

    spare_parts = df.loc[spare_mask, [COL_ARTICLE, COL_SECTION, COL_IMAGE]].copy()
    spare_parts[COL_IMAGE] = PLACEHOLDER_PATH

    other_missing = df.loc[empty_mask & ~spare_mask, [COL_ARTICLE, COL_SECTION, COL_IMAGE]].copy()
    other_missing = other_missing.sort_values([COL_SECTION, COL_ARTICLE], kind="stable")
    other_missing_with_article = other_missing[
        ~other_missing[COL_ARTICLE].map(is_empty_image)
    ].copy()

    summary = pd.DataFrame(
        [
            {"metric": "total_rows", "value": int(len(df))},
            {"metric": "spare_parts_rows", "value": int(spare_mask.sum())},
            {"metric": "spare_parts_missing_before_fill", "value": int((spare_mask & empty_mask).sum())},
            {"metric": "other_missing_rows_all", "value": int((empty_mask & ~spare_mask).sum())},
            {"metric": "other_missing_rows_with_article", "value": int(len(other_missing_with_article))},
            {"metric": "placeholder_path", "value": PLACEHOLDER_PATH},
        ]
    )

    with pd.ExcelWriter(OUTPUT_XLSX, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="summary", index=False)
        spare_parts.to_excel(writer, sheet_name="spare_parts_import", index=False)
        other_missing.to_excel(writer, sheet_name="other_missing_all", index=False)
        other_missing_with_article.to_excel(writer, sheet_name="other_missing_with_article", index=False)

    print(f"Saved: {OUTPUT_XLSX}")
    print(f"Spare parts rows: {len(spare_parts)}")
    print(f"Other missing rows (all): {len(other_missing)}")
    print(f"Other missing rows (with article): {len(other_missing_with_article)}")


if __name__ == "__main__":
    main()
