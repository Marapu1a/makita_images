from __future__ import annotations

from pathlib import Path

import pandas as pd


FINAL_DIR = Path(__file__).resolve().parent
FINAL_REPORT_XLSX = FINAL_DIR / "final_report.xlsx"
IMPORT_XLSX = FINAL_DIR / "pictures_for_import.xlsx"
BITRIX_XLSX = FINAL_DIR / "pictures_for_bitrix_import.xlsx"


def build_gallery(value: str, folder: str, bitrix: bool) -> str:
    if pd.isna(value) or not str(value).strip() or str(value).strip().lower() == "nan":
        return ""
    files = [x.strip() for x in str(value).split("|") if x and x.strip() and x.strip().lower() != "nan"]
    if bitrix:
        return ";".join(f"/upload/vvm_images/import_images/{folder}/{name}" for name in files)
    return ";".join(f"/final_elitech_and_teh_delivery_2026-04-27/import_images/{folder}/{name}" for name in files)


def main() -> None:
    report = pd.read_excel(FINAL_REPORT_XLSX)
    report = report[report["preview_name"].fillna("") != ""].copy()

    plain_rows = []
    bitrix_rows = []
    for row in report.to_dict("records"):
        article = row["Артикул [ARTIKUL]"]
        folder = row["folder_name"]
        preview_name = row["preview_name"]
        if pd.isna(preview_name) or not str(preview_name).strip() or str(preview_name).strip().lower() == "nan":
            continue
        gallery_names = row.get("gallery_names", "")

        plain_rows.append(
            {
                "Артикул [ARTIKUL]": article,
                "Картинка для анонса (путь)": f"/final_elitech_and_teh_delivery_2026-04-27/import_images/{folder}/{preview_name}",
                "Картинки галереи [MORE_PHOTO]": build_gallery(gallery_names, folder, bitrix=False),
            }
        )
        bitrix_rows.append(
            {
                "Артикул [ARTIKUL]": article,
                "Картинка для анонса (путь)": f"/upload/vvm_images/import_images/{folder}/{preview_name}",
                "Картинки галереи [MORE_PHOTO]": build_gallery(gallery_names, folder, bitrix=True),
            }
        )

    pd.DataFrame(plain_rows).to_excel(IMPORT_XLSX, index=False)
    bitrix_df = pd.DataFrame(bitrix_rows)
    bitrix_df.to_excel(BITRIX_XLSX, index=False)
    print("rows", len(plain_rows))
    print("bitrix_saved_to", BITRIX_XLSX)


if __name__ == "__main__":
    main()
