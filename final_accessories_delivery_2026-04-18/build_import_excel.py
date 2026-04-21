from __future__ import annotations

from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
FINAL_REPORT_FILE = BASE_DIR / "final_report.xlsx"
IMAGES_DIR = BASE_DIR / "import_images"
OUTPUT_FILE = BASE_DIR / "pictures_for_import.xlsx"
BITRIX_OUTPUT_FILE = BASE_DIR / "pictures_for_bitrix_import.xlsx"

ARTICLE_COL = "Артикул [ARTIKUL]"
PREVIEW_COL = "Картинка для анонса (путь)"
MORE_PHOTO_COL = "Картинки галереи [MORE_PHOTO]"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def is_image_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def sort_images(files: list[Path]) -> list[Path]:
    return sorted(
        files,
        key=lambda p: (
            0 if p.stem.lower() == "preview" else 1,
            p.name.lower(),
        ),
    )


def build_web_path(article: str, filename: str) -> str:
    return f"/final_accessories_delivery_2026-04-18/import_images/{article}/{filename}"


def build_bitrix_web_path(article: str, filename: str) -> str:
    return f"/upload/vvm_images/import_images/{article}/{filename}"


def get_paths(folder: Path, article: str, builder) -> tuple[str, str]:
    image_files = [p for p in folder.iterdir() if is_image_file(p)]
    if not image_files:
        return "", ""

    image_files = sort_images(image_files)
    preview_file = None
    gallery_files: list[Path] = []

    for file in image_files:
        if file.stem.lower() == "preview":
            preview_file = file
        else:
            gallery_files.append(file)

    if preview_file is None:
        preview_file = image_files[0]
        gallery_files = image_files[1:]

    preview_path = builder(article, preview_file.name)
    gallery_paths = [builder(article, file.name) for file in gallery_files]
    return preview_path, ";".join(gallery_paths)


def main() -> None:
    if not FINAL_REPORT_FILE.exists():
        raise FileNotFoundError(f"Final report not found: {FINAL_REPORT_FILE}")
    if not IMAGES_DIR.exists():
        raise FileNotFoundError(f"Images directory not found: {IMAGES_DIR}")

    report_df = pd.read_excel(FINAL_REPORT_FILE)

    rows: list[dict] = []
    gallery_count = 0
    placeholder_count = 0
    for _, row in report_df.iterrows():
        article = str(row.get("article", "")).strip()
        if not article:
            continue
        folder_name = str(row.get("folder_name", article)).strip()
        folder = IMAGES_DIR / folder_name
        if not folder.exists():
            continue
        preview_path, more_photo_path = get_paths(folder, folder_name, build_web_path)
        if not preview_path:
            continue
        if more_photo_path:
            gallery_count += 1
        if str(row.get("placeholder_used", "")).strip().upper() == "YES":
            placeholder_count += 1
        rows.append(
            {
                ARTICLE_COL: article,
                PREVIEW_COL: preview_path,
                MORE_PHOTO_COL: more_photo_path,
            }
        )

    output_df = pd.DataFrame(rows, columns=[ARTICLE_COL, PREVIEW_COL, MORE_PHOTO_COL])
    output_df.to_excel(OUTPUT_FILE, index=False)

    bitrix_rows: list[dict] = []
    for _, row in report_df.iterrows():
        article = str(row.get("article", "")).strip()
        if not article:
            continue
        folder_name = str(row.get("folder_name", article)).strip()
        folder = IMAGES_DIR / folder_name
        if not folder.exists():
            continue
        preview_path, more_photo_path = get_paths(folder, folder_name, build_bitrix_web_path)
        if not preview_path:
            continue
        bitrix_rows.append(
            {
                ARTICLE_COL: article,
                PREVIEW_COL: preview_path,
                MORE_PHOTO_COL: more_photo_path,
            }
        )

    bitrix_df = pd.DataFrame(bitrix_rows, columns=[ARTICLE_COL, PREVIEW_COL, MORE_PHOTO_COL])
    bitrix_df.to_excel(BITRIX_OUTPUT_FILE, index=False)

    print("\n=== ACCESSORIES IMPORT EXCEL SUMMARY ===")
    print(f"Rows exported: {len(output_df)}")
    print(f"Rows with gallery images: {gallery_count}")
    print(f"Rows with placeholder preview: {placeholder_count}")
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"Saved to: {BITRIX_OUTPUT_FILE}")


if __name__ == "__main__":
    main()
