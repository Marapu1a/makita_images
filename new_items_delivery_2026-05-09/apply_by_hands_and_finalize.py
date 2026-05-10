from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import requests
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
BY_HANDS_DIR = ROOT_DIR / "by_hands"
IMPORT_DIR = BASE_DIR / "import_images"
FINAL_REPORT_XLSX = BASE_DIR / "final_report.xlsx"
SUMMARY_XLSX = BASE_DIR / "summary.xlsx"
REMAINING_XLSX = BASE_DIR / "remaining_placeholders.xlsx"
IMPORT_XLSX = BASE_DIR / "pictures_for_import.xlsx"
BITRIX_XLSX = BASE_DIR / "pictures_for_bitrix_import.xlsx"
PLACEHOLDER_FILE = ROOT_DIR / "placeholder.webp"

WEBP_QUALITY = 90
WEBP_METHOD = 6
MAX_WIDTH = 1600
MAX_HEIGHT = 1600


def prepare_image(image: Image.Image) -> Image.Image:
    has_alpha = image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)
    image = image.convert("RGBA" if has_alpha else "RGB")
    image.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.LANCZOS)
    if image.mode == "RGBA":
        background = Image.new("RGB", image.size, "white")
        background.paste(image, mask=image.getchannel("A"))
        return background
    return image.convert("RGB")


def save_as_webp(source_path: Path, target_path: Path) -> None:
    with Image.open(source_path) as image:
        prepared = prepare_image(image)
        prepared.save(target_path, format="WEBP", quality=WEBP_QUALITY, method=WEBP_METHOD)


def normalize_manual_folder(article: str) -> int:
    src_dir = BY_HANDS_DIR / article
    dst_dir = IMPORT_DIR / article
    if dst_dir.exists():
        shutil.rmtree(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)

    image_files = sorted(p for p in src_dir.iterdir() if p.is_file())
    if not image_files:
        return 0

    save_as_webp(image_files[0], dst_dir / "preview.webp")
    for idx, path in enumerate(image_files[1:], start=1):
        save_as_webp(path, dst_dir / f"gallery_{idx:02d}.webp")
    return len(image_files)


def ensure_placeholder_folder(article: str) -> int:
    dst_dir = IMPORT_DIR / article
    if dst_dir.exists():
        shutil.rmtree(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PLACEHOLDER_FILE, dst_dir / "preview.webp")
    return 1


def gallery_value(folder_name: str) -> str:
    folder = IMPORT_DIR / folder_name
    gallery_files = sorted(p.name for p in folder.glob("gallery_*.webp"))
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

    manual_articles = sorted(p.name for p in BY_HANDS_DIR.iterdir() if p.is_dir())
    manual_set = {article.upper() for article in manual_articles}

    for article in manual_articles:
        image_count = normalize_manual_folder(article)
        mask = report["article"].astype(str).str.upper() == article.upper()
        if not mask.any():
            continue
        report.loc[mask, "final_status"] = "REAL_IMAGE"
        report.loc[mask, "source"] = "by_hands"
        report.loc[mask, "source_url"] = "manual"
        report.loc[mask, "folder_name"] = article
        report.loc[mask, "image_count"] = image_count
        report.loc[mask, "placeholder_used"] = "NO"

    remaining_mask = report["placeholder_used"].astype(str).str.upper() == "YES"
    remaining_articles = sorted(report.loc[remaining_mask, "article"].astype(str).tolist())
    for article in remaining_articles:
        if article.upper() in manual_set:
            continue
        image_count = ensure_placeholder_folder(article)
        mask = report["article"].astype(str).str.upper() == article.upper()
        report.loc[mask, "final_status"] = "PLACEHOLDER"
        report.loc[mask, "source"] = "placeholder"
        report.loc[mask, "source_url"] = ""
        report.loc[mask, "folder_name"] = article
        report.loc[mask, "image_count"] = image_count
        report.loc[mask, "placeholder_used"] = "YES"

    report.to_excel(FINAL_REPORT_XLSX, index=False)
    rebuild_exports(report)

    real_count = int((report["final_status"].astype(str).str.upper() == "REAL_IMAGE").sum())
    placeholder_count = int((report["placeholder_used"].astype(str).str.upper() == "YES").sum())
    print(f"Manual folders applied: {len(manual_articles)}")
    print(f"Real image rows: {real_count}")
    print(f"Placeholder rows: {placeholder_count}")


if __name__ == "__main__":
    main()
