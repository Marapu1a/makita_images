from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
IMPORT_DIR = BASE_DIR / "import_images"
FINAL_REPORT_XLSX = BASE_DIR / "final_report.xlsx"
SUMMARY_XLSX = BASE_DIR / "summary.xlsx"
REMAINING_XLSX = BASE_DIR / "remaining_placeholders.xlsx"
IMPORT_XLSX = BASE_DIR / "pictures_for_import.xlsx"
BITRIX_XLSX = BASE_DIR / "pictures_for_bitrix_import.xlsx"
SOURCE_IMPORT_DIR = BASE_DIR.parent / "iterations" / "new_items_2026-05-09" / "makita" / "output" / "import_images"


UPDATES: dict[str, dict[str, str]] = {
    "LM003GU102": {
        "source": "makitarussia.ru",
        "source_url": "https://makitarussia.ru/product/gazonokosilka-akkumulyatornaya-38sm-40v-makita-lm003gu102/",
    },
    "LM004GU102": {
        "source": "makitarussia.ru",
        "source_url": "https://makitarussia.ru/product/gazonokosilka-akkumulyatornaya-43sm-40v-makita-lm004gu102/",
    },
    "632F59-1": {
        "source": "makitarussia.ru",
        "source_url": "https://makitarussia.ru/product/632f59-1/",
    },
    "1915P2-0": {
        "source": "makita.co.nz",
        "source_url": "https://www.makita.co.nz/accessories/item/cleaning-2261",
    },
    "1914X6-2": {
        "source": "makita.co.nz",
        "source_url": "https://www.makita.co.nz/accessories/item/cleaning-1121",
    },
}


def gallery_value(folder_name: str) -> str:
    folder = IMPORT_DIR / folder_name
    gallery_files = sorted([p.name for p in folder.glob("gallery_*.webp")])
    if not gallery_files:
        return ""
    return "|".join(f"/upload/vvm_images/import_images/{folder_name}/{name}" for name in gallery_files)


def preview_value(folder_name: str) -> str:
    return f"/upload/vvm_images/import_images/{folder_name}/preview.webp"


def rebuild_exports(report: pd.DataFrame) -> None:
    summary = (
        report.groupby(["project_block", "final_status"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["project_block", "final_status"])
    )
    summary.to_excel(SUMMARY_XLSX, index=False)

    placeholders = report[report["placeholder_used"].astype(str).str.upper() == "YES"].copy()
    with pd.ExcelWriter(REMAINING_XLSX, engine="openpyxl") as writer:
        placeholders.to_excel(writer, sheet_name="all_placeholders", index=False)
        for project_block, group in placeholders.groupby("project_block", dropna=False):
            group.to_excel(writer, sheet_name=str(project_block)[:31], index=False)

    export = report.copy()
    export["Артикул [ARTIKUL]"] = export["article"]
    export["Картинка для анонса (путь)"] = export["folder_name"].map(preview_value)
    export["Картинки галереи [MORE_PHOTO]"] = export["folder_name"].map(gallery_value)
    cols = ["Артикул [ARTIKUL]", "Картинка для анонса (путь)", "Картинки галереи [MORE_PHOTO]"]
    export[cols].to_excel(IMPORT_XLSX, index=False)
    export[cols].to_excel(BITRIX_XLSX, index=False)


def main() -> None:
    report = pd.read_excel(FINAL_REPORT_XLSX)

    for article, meta in UPDATES.items():
        src = SOURCE_IMPORT_DIR / article
        dst = IMPORT_DIR / article
        if not src.exists():
            continue
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

        mask = report["article"].astype(str).str.upper() == article.upper()
        if not mask.any():
            continue
        image_count = len(list(dst.glob("*.webp")))
        report.loc[mask, "final_status"] = "REAL_IMAGE"
        report.loc[mask, "source"] = meta["source"]
        report.loc[mask, "source_url"] = meta["source_url"]
        report.loc[mask, "folder_name"] = article
        report.loc[mask, "image_count"] = image_count
        report.loc[mask, "placeholder_used"] = "NO"

    report.to_excel(FINAL_REPORT_XLSX, index=False)
    rebuild_exports(report)
    remaining = (report["placeholder_used"].astype(str).str.upper() == "YES").sum()
    print(f"Updated rows: {len(UPDATES)}")
    print(f"Remaining placeholders: {remaining}")


if __name__ == "__main__":
    main()
