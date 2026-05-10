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

TAIL_DIR = (
    BASE_DIR.parent
    / "iterations"
    / "new_items_2026-05-09"
    / "elitech_tail_exact_2026-05-09"
    / "output"
    / "import_images"
)
MODEL_DIR = (
    BASE_DIR.parent
    / "iterations"
    / "new_items_2026-05-09"
    / "elitech_tail_model_2026-05-09"
    / "output"
    / "import_images"
)


EXACT_UPDATES: dict[str, dict[str, str]] = {
    "160682": {
        "source": "vseinstrumenti.ru exact image",
        "source_url": "https://www.vseinstrumenti.ru/product/svarochnyj-invertor-elitech-ais-140sa-92879/",
    },
    "202233": {
        "source": "invoz.ru exact product page",
        "source_url": "https://www.invoz.ru/catalog/vsye_dlya_sada/pily_tsepnye/benzopily/pila_tsepnaya_benz_bp_45_18_prof.html",
    },
    "206444": {
        "source": "elitech-m.ru near-family variant",
        "source_url": "https://elitech-m.ru/item-id-1860656/",
    },
    "203564": {
        "source": "piterinstrument.ru exact product page",
        "source_url": "https://piterinstrument.ru/__akkumulyatorniy-instrument/dreli-shurupoverti/drel-akkumulyatornaya-elitech-da-20-2sl-e220102301--i/",
    },
    "201307": {
        "source": "makitapro.ru exact product page",
        "source_url": "https://www.makitapro.ru/Maslyanyj-kompressor-Elitech-KPM-300-24-Promo-%28E0503.003.00%29-i17006.html",
    },
    "204449": {
        "source": "makitapro.ru exact product page",
        "source_url": "https://www.makitapro.ru/Perforator-Elitech-P-0724REM-Promo-i17223.html",
    },
    "207969": {
        "source": "makita-profi.ru exact product page",
        "source_url": "https://makita-profi.ru/plitkorez-elektricheskij-pe-08-20r06-e200801500/",
    },
}

MODEL_UPDATES: dict[str, dict[str, str]] = {
    "196375": {"source": "elitech-m.ru model tail", "source_url": "https://elitech-m.ru/item-id-1864108/"},
    "196376": {"source": "elitech-m.ru model tail", "source_url": "https://elitech-m.ru/item-id-1864157/"},
    "155209": {"source": "elitech-m.ru model tail", "source_url": "https://elitech-m.ru/item-id-1864294/"},
    "199936": {"source": "elitech-m.ru model tail", "source_url": "https://elitech-m.ru/item-id-1865183/"},
    "205904": {"source": "elitech-m.ru model tail", "source_url": "https://elitech-m.ru/item-id-1864168/"},
    "205905": {"source": "elitech-m.ru model tail", "source_url": "https://elitech-m.ru/item-id-1860791/"},
    "206451": {"source": "elitech-m.ru model tail", "source_url": "https://elitech-m.ru/item-id-1881234/"},
    "191977": {"source": "elitech-m.ru model tail", "source_url": "https://elitech-m.ru/item-id-1864174/"},
    "187850": {"source": "elitech-m.ru model tail", "source_url": "https://elitech-m.ru/item-id-1864248/"},
    "185367": {"source": "elitech-m.ru model tail", "source_url": "https://elitech-m.ru/item-id-1865318/"},
    "211368": {"source": "elitech-m.ru model tail", "source_url": "https://elitech-m.ru/item-id-1879773/"},
}


def gallery_value(folder_name: str) -> str:
    folder = IMPORT_DIR / folder_name
    gallery_files = sorted(
        [p.name for p in folder.glob("gallery_*.webp") if p.name.lower() != "preview.webp"]
    )
    if not gallery_files:
        return ""
    return "|".join(f"/upload/vvm_images/import_images/{folder_name}/{name}" for name in gallery_files)


def preview_value(folder_name: str) -> str:
    return f"/upload/vvm_images/import_images/{folder_name}/preview.webp"


def main() -> None:
    all_updates = {**MODEL_UPDATES, **EXACT_UPDATES}

    for article, meta in MODEL_UPDATES.items():
        src = MODEL_DIR / article
        dst = IMPORT_DIR / article
        if not src.exists():
            continue
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

    for article, meta in EXACT_UPDATES.items():
        src = TAIL_DIR / article
        dst = IMPORT_DIR / article
        if not src.exists():
            continue
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

    report = pd.read_excel(FINAL_REPORT_XLSX)
    for article, meta in all_updates.items():
        mask = report["article"].astype(str).str.upper() == article.upper()
        if not mask.any():
            continue
        image_count = len(list((IMPORT_DIR / article).glob("*.webp")))
        report.loc[mask, "final_status"] = "REAL_IMAGE"
        report.loc[mask, "source"] = meta["source"]
        report.loc[mask, "source_url"] = meta["source_url"]
        report.loc[mask, "folder_name"] = article
        report.loc[mask, "image_count"] = image_count
        report.loc[mask, "placeholder_used"] = "NO"

    report.to_excel(FINAL_REPORT_XLSX, index=False)

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
            safe_name = str(project_block)[:31] if project_block else "unknown"
            group.to_excel(writer, sheet_name=safe_name, index=False)

    import_df = report.copy()
    import_df["Артикул [ARTIKUL]"] = import_df["article"]
    import_df["Картинка для анонса (путь)"] = import_df["folder_name"].map(preview_value)
    import_df["Картинки галереи [MORE_PHOTO]"] = import_df["folder_name"].map(gallery_value)
    export_cols = [
        "Артикул [ARTIKUL]",
        "Картинка для анонса (путь)",
        "Картинки галереи [MORE_PHOTO]",
    ]
    import_df[export_cols].to_excel(IMPORT_XLSX, index=False)
    import_df[export_cols].to_excel(BITRIX_XLSX, index=False)

    print(f"Updated rows: {len(all_updates)}")
    print(f"Remaining placeholders: {len(placeholders)}")


if __name__ == "__main__":
    main()
