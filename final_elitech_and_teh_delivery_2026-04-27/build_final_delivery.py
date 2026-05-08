from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BASELINE_XLSX = ROOT / "iterations" / "elitech_and_teh" / "elitech_and_teh_without_images.xlsx"
FINAL_DIR = Path(__file__).resolve().parent
IMPORT_DIR = FINAL_DIR / "import_images"
FINAL_REPORT_XLSX = FINAL_DIR / "final_report.xlsx"

SOURCES = [
    {
        "key": "elitech_official",
        "label": "elitech.ru official product pages",
        "dir": ROOT / "iterations" / "elitech_and_teh" / "elitech_official_2026-04-27" / "output" / "import_images",
        "priority": 10,
    },
    {
        "key": "teh_russia",
        "label": "teh-russia.ru",
        "dir": ROOT / "iterations" / "elitech_and_teh" / "teh_russia_2026-04-27" / "output" / "import_images",
        "priority": 20,
    },
    {
        "key": "elitech_catalog_pdf",
        "label": "ELITECH_2025 catalog exact article crops",
        "dir": ROOT / "iterations" / "elitech_and_teh" / "elitech_catalog_pdf_2026-04-27" / "output" / "import_images",
        "priority": 30,
    },
    {
        "key": "elitech_m",
        "label": "elitech-m.ru + makita-land cross-check",
        "dir": ROOT / "iterations" / "elitech_and_teh" / "elitech_m_2026-04-27" / "output" / "import_images",
        "priority": 40,
    },
    {
        "key": "elitech_catalog_family_pdf",
        "label": "ELITECH_2025 catalog family layer",
        "dir": ROOT / "iterations" / "elitech_and_teh" / "elitech_catalog_family_pdf_2026-04-27" / "output" / "import_images",
        "priority": 50,
    },
]


def norm_article(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().upper()


def safe_folder_name(article: str) -> str:
    return article.replace("/", "_").replace("\\", "_")


def detect_article_col(df: pd.DataFrame) -> str:
    for col in df.columns:
        if "ARTIKUL" in str(col).upper():
            return col
    raise RuntimeError("Article column not found")


def copy_tree(src: Path, dst: Path) -> tuple[str, list[str]]:
    dst.mkdir(parents=True, exist_ok=True)
    preview = ""
    gallery_files: list[str] = []
    for file in sorted(src.glob("*.webp")):
        shutil.copy2(file, dst / file.name)
        if file.name == "preview.webp":
            preview = file.name
        elif file.name.startswith("gallery_"):
            gallery_files.append(file.name)
    return preview, gallery_files


def main() -> None:
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)

    baseline = pd.read_excel(BASELINE_XLSX)
    article_col = detect_article_col(baseline)
    baseline["_article_norm"] = baseline[article_col].map(norm_article)

    source_maps: dict[str, set[str]] = {}
    for source in SOURCES:
        articles = set()
        if source["dir"].exists():
            for folder in source["dir"].iterdir():
                if folder.is_dir() and (folder / "preview.webp").exists():
                    articles.add(norm_article(folder.name))
        source_maps[source["key"]] = articles

    rows = []
    for row in baseline.to_dict("records"):
        article = str(row[article_col]).strip()
        article_norm = row["_article_norm"]
        chosen = None
        for source in SOURCES:
            if article_norm in source_maps[source["key"]]:
                chosen = source
                break

        final_folder = safe_folder_name(article)
        preview_name = ""
        gallery_names: list[str] = []
        chosen_key = ""
        chosen_label = ""

        if chosen is not None:
            src_folder = chosen["dir"] / final_folder
            if not src_folder.exists():
                src_folder = chosen["dir"] / article_norm
            if src_folder.exists():
                preview_name, gallery_names = copy_tree(src_folder, IMPORT_DIR / final_folder)
                chosen_key = chosen["key"]
                chosen_label = chosen["label"]

        source_hits = {f"hit_{s['key']}": article_norm in source_maps[s["key"]] for s in SOURCES}
        rows.append(
            {
                article_col: article,
                "name": row.get("Наименование элемента", ""),
                "main_section": row.get("Название основного раздела", ""),
                "chosen_source_key": chosen_key,
                "chosen_source_label": chosen_label,
                "folder_name": final_folder,
                "preview_name": preview_name,
                "gallery_names": "|".join(gallery_names),
                "image_count": int(bool(preview_name)) + len(gallery_names),
                **source_hits,
            }
        )

    report = pd.DataFrame(rows)
    report.to_excel(FINAL_REPORT_XLSX, index=False)
    print("rows", len(report))
    print("covered", (report["preview_name"] != "").sum())


if __name__ == "__main__":
    main()
