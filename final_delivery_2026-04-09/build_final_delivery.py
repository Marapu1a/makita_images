from __future__ import annotations

from pathlib import Path
import re
import shutil

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
FINAL_DIR = Path(__file__).resolve().parent
FINAL_IMAGES_DIR = FINAL_DIR / "import_images"
FINAL_REPORT_FILE = FINAL_DIR / "final_report.xlsx"
PLACEHOLDER_FILE = ROOT_DIR / "placeholder.webp"

BASELINE_FILE = ROOT_DIR / "iterations" / "makitakirov_2026-04-08" / "work" / "tools_without_images.xlsx"
MK_REPORT_FILE = ROOT_DIR / "iterations" / "makitakirov_2026-04-08" / "output" / "makitakirov_report.xlsx"
MP_REPORT_FILE = ROOT_DIR / "iterations" / "makitapro_2026-04-08" / "output" / "makitapro_report.xlsx"
MO_REPORT_FILE = ROOT_DIR / "iterations" / "makita_one_2026-04-08" / "output" / "makita_one_report.xlsx"

MK_IMAGES_DIR = ROOT_DIR / "iterations" / "makitakirov_2026-04-08" / "output" / "import_images"
MP_IMAGES_DIR = ROOT_DIR / "iterations" / "makitapro_2026-04-08" / "output" / "import_images"
MO_IMAGES_DIR = ROOT_DIR / "iterations" / "makita_one_2026-04-08" / "output" / "import_images"

ITERATION_SOURCES = [
    {
        "iteration": "makitakirov_2026-04-08",
        "site": "makitakirov.rf",
        "images_dir": MK_IMAGES_DIR,
        "report_file": MK_REPORT_FILE,
        "status_column": "makitakirov_status",
        "note_column": "makitakirov_note",
        "url_column": "makitakirov_product_url",
    },
    {
        "iteration": "makitapro_2026-04-08",
        "site": "makitapro.ru",
        "images_dir": MP_IMAGES_DIR,
        "report_file": MP_REPORT_FILE,
        "status_column": "makitapro_status",
        "note_column": "makitapro_note",
        "url_column": "makitapro_product_url",
    },
    {
        "iteration": "makita_one_2026-04-08",
        "site": "makita.one",
        "images_dir": MO_IMAGES_DIR,
        "report_file": MO_REPORT_FILE,
        "status_column": "makita_one_status",
        "note_column": "makita_one_note",
        "url_column": "makita_one_product_url",
    },
]


def normalize_article(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().upper()
    return re.sub(r"\s+", "", text)


def find_article_column(columns: list[str]) -> str:
    for column in columns:
        if "ARTIKUL" in str(column).upper():
            return column
    raise ValueError("Could not find article column")


def folder_has_preview(folder: Path) -> bool:
    return folder.is_dir() and (folder / "preview.webp").exists()


def load_baseline() -> tuple[pd.DataFrame, str]:
    df = pd.read_excel(BASELINE_FILE)
    article_col = find_article_column(df.columns.tolist())
    work_df = df.copy()
    work_df["_article_norm"] = work_df[article_col].map(normalize_article)
    work_df = work_df[work_df["_article_norm"] != ""].copy()
    work_df = work_df.drop_duplicates(subset=["_article_norm"]).reset_index(drop=True)
    return work_df, article_col


def load_report_map(report_file: Path) -> dict[str, dict]:
    df = pd.read_excel(report_file)
    result: dict[str, dict] = {}
    for _, row in df.iterrows():
        article = normalize_article(row.get("article"))
        if not article:
            continue
        result[article] = {
            "status": row.get("status", ""),
            "note": row.get("note", ""),
            "product_url": row.get("product_url", ""),
        }
    return result


def copy_real_folder(source_dir: Path, target_dir: Path) -> None:
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir)


def create_placeholder_folder(target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PLACEHOLDER_FILE, target_dir / "preview.webp")


def main() -> None:
    if not PLACEHOLDER_FILE.exists():
        raise FileNotFoundError(f"Placeholder file not found: {PLACEHOLDER_FILE}")

    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    if FINAL_IMAGES_DIR.exists():
        shutil.rmtree(FINAL_IMAGES_DIR)
    FINAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    baseline_df, article_col = load_baseline()

    report_maps = {
        source["iteration"]: load_report_map(source["report_file"])
        for source in ITERATION_SOURCES
    }

    rows: list[dict] = []
    real_count = 0
    placeholder_count = 0

    for _, row in baseline_df.iterrows():
        article = normalize_article(row[article_col])
        target_dir = FINAL_IMAGES_DIR / article

        final_status = "PLACEHOLDER"
        final_iteration = "placeholder"
        final_site = "placeholder"
        final_note = "placeholder_used"

        for source in ITERATION_SOURCES:
            source_folder = source["images_dir"] / article
            if folder_has_preview(source_folder):
                copy_real_folder(source_folder, target_dir)
                final_status = "REAL_IMAGE"
                final_iteration = source["iteration"]
                final_site = source["site"]
                final_note = "real_images_copied"
                real_count += 1
                break

        if final_status == "PLACEHOLDER":
            create_placeholder_folder(target_dir)
            placeholder_count += 1

        report_row = {
            "article": article,
            "name": row.get("Наименование элемента", ""),
            "final_status": final_status,
            "final_iteration": final_iteration,
            "final_site": final_site,
            "final_folder": article,
            "final_note": final_note,
            "placeholder_used": "YES" if final_status == "PLACEHOLDER" else "NO",
        }

        for source in ITERATION_SOURCES:
            item = report_maps[source["iteration"]].get(article, {})
            report_row[source["status_column"]] = item.get("status", "")
            report_row[source["note_column"]] = item.get("note", "")
            report_row[source["url_column"]] = item.get("product_url", "")

        rows.append(report_row)

    report_df = pd.DataFrame(rows)
    report_df = report_df.sort_values(by=["placeholder_used", "article"], ascending=[True, True]).reset_index(drop=True)
    report_df.to_excel(FINAL_REPORT_FILE, index=False)

    print("\n=== FINAL DELIVERY SUMMARY ===")
    print(f"Baseline rows with article: {len(baseline_df)}")
    print(f"Real image folders copied: {real_count}")
    print(f"Placeholder folders created: {placeholder_count}")
    print(f"Final images dir: {FINAL_IMAGES_DIR}")
    print(f"Final report: {FINAL_REPORT_FILE}")


if __name__ == "__main__":
    main()
