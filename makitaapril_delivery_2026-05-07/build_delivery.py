from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re

import pandas as pd
from PIL import Image


ROOT_DIR = Path(r"C:\Users\Valentine\Desktop\makita\py_makita\upload")
SOURCE_DIR = ROOT_DIR / "макитаапрель"
PLACEHOLDER_FILE = ROOT_DIR / "placeholder_items_2026-04-27.xlsx"

BASE_DIR = Path(__file__).resolve().parent
IMAGES_DIR = BASE_DIR / "import_images"
REPORT_FILE = BASE_DIR / "final_report.xlsx"
IMPORT_FILE = BASE_DIR / "pictures_for_import.xlsx"
BITRIX_IMPORT_FILE = BASE_DIR / "pictures_for_bitrix_import.xlsx"

ARTICLE_COL = "Артикул [ARTIKUL]"
PREVIEW_COL = "Картинка для анонса (путь)"
MORE_PHOTO_COL = "Картинки галереи [MORE_PHOTO]"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
WEBP_QUALITY = 84
WEBP_METHOD = 6
MAX_WIDTH = 1600
MAX_HEIGHT = 1600

Image.MAX_IMAGE_PIXELS = None


def is_image_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def normalize_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def safe_folder_name(value: str) -> str:
    text = normalize_text(value)
    text = re.sub(r"[^\w\-.]+", "_", text)
    return text[:120]


def natural_sort_key(path: Path) -> tuple:
    parts = re.split(r"(\d+)", path.name.lower())
    key: list[object] = []
    for part in parts:
        if part.isdigit():
            key.append(int(part))
        else:
            key.append(part)
    return tuple(key)


def prepare_image(image: Image.Image) -> Image.Image:
    has_alpha = image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)
    image = image.convert("RGBA" if has_alpha else "RGB")
    image.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.LANCZOS)
    return image


def convert_image(src: Path, dst: Path) -> None:
    with Image.open(src) as image:
        image = prepare_image(image)
        image.save(dst, format="WEBP", quality=WEBP_QUALITY, method=WEBP_METHOD)


def build_web_path(folder_name: str, filename: str) -> str:
    return f"/makitaapril_delivery_2026-05-07/import_images/{folder_name}/{filename}"


def build_bitrix_web_path(folder_name: str, filename: str) -> str:
    return f"/upload/vvm_images/import_images/{folder_name}/{filename}"


def main() -> None:
    if not SOURCE_DIR.exists():
        raise FileNotFoundError(f"Source dir not found: {SOURCE_DIR}")
    if not PLACEHOLDER_FILE.exists():
        raise FileNotFoundError(f"Placeholder file not found: {PLACEHOLDER_FILE}")

    BASE_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    placeholder_df = pd.read_excel(PLACEHOLDER_FILE)
    placeholder_df["article_str"] = placeholder_df["article"].map(normalize_text).str.upper()
    placeholder_df["folder_str"] = placeholder_df["folder_name"].map(normalize_text).str.upper()

    manual_folders = {p.name.upper(): p for p in SOURCE_DIR.iterdir() if p.is_dir()}
    found_df = placeholder_df[placeholder_df["folder_str"].isin(manual_folders)].copy()
    found_df.sort_values(["project_block", "article_str"], inplace=True)

    report_rows: list[dict] = []
    import_rows: list[dict] = []
    bitrix_rows: list[dict] = []

    for _, row in found_df.iterrows():
        article = normalize_text(row["article"])
        project_block = normalize_text(row["project_block"])
        name = normalize_text(row["name"])
        source_folder_name = normalize_text(row["folder_name"])
        source_folder = manual_folders[source_folder_name.upper()]
        target_folder_name = safe_folder_name(source_folder_name)
        target_folder = IMAGES_DIR / target_folder_name
        target_folder.mkdir(parents=True, exist_ok=True)

        image_files = sorted([p for p in source_folder.iterdir() if is_image_file(p)], key=natural_sort_key)
        if not image_files:
            continue

        converted_names: list[str] = []
        for idx, src_image in enumerate(image_files):
            if idx == 0:
                filename = "preview.webp"
            else:
                filename = f"gallery_{idx:02d}.webp"
            dst_image = target_folder / filename
            convert_image(src_image, dst_image)
            converted_names.append(filename)

        preview_name = converted_names[0]
        gallery_names = converted_names[1:]

        import_rows.append(
            {
                ARTICLE_COL: article,
                PREVIEW_COL: build_web_path(target_folder_name, preview_name),
                MORE_PHOTO_COL: ";".join(build_web_path(target_folder_name, name) for name in gallery_names),
            }
        )
        bitrix_rows.append(
            {
                ARTICLE_COL: article,
                PREVIEW_COL: build_bitrix_web_path(target_folder_name, preview_name),
                MORE_PHOTO_COL: ";".join(build_bitrix_web_path(target_folder_name, name) for name in gallery_names),
            }
        )
        report_rows.append(
            {
                "project_block": project_block,
                "article": article,
                "name": name,
                "source_folder_name": source_folder_name,
                "target_folder_name": target_folder_name,
                "source_file_count": len(image_files),
                "converted_file_count": len(converted_names),
                "preview_name": preview_name,
                "gallery_names": "|".join(gallery_names),
                "source_dir": str(source_folder),
            }
        )

    report_df = pd.DataFrame(report_rows)
    report_df.to_excel(REPORT_FILE, index=False)

    import_df = pd.DataFrame(import_rows, columns=[ARTICLE_COL, PREVIEW_COL, MORE_PHOTO_COL])
    import_df.to_excel(IMPORT_FILE, index=False)

    bitrix_df = pd.DataFrame(bitrix_rows, columns=[ARTICLE_COL, PREVIEW_COL, MORE_PHOTO_COL])
    bitrix_df.to_excel(BITRIX_IMPORT_FILE, index=False)

    print("=== MAKITAAPRIL DELIVERY SUMMARY ===")
    print(f"Rows exported: {len(import_df)}")
    print(f"Image folders exported: {len(report_df)}")
    print(f"Total webp files: {sum(len(list(folder.iterdir())) for folder in IMAGES_DIR.iterdir() if folder.is_dir())}")
    print(f"Saved report: {REPORT_FILE}")
    print(f"Saved import: {IMPORT_FILE}")
    print(f"Saved Bitrix import: {BITRIX_IMPORT_FILE}")


if __name__ == "__main__":
    main()
