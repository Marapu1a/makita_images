from __future__ import annotations

from pathlib import Path
import re

import pandas as pd
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
IMAGES_DIR = BASE_DIR / "import_images"
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


def needs_normalization(files: list[Path]) -> bool:
    if not files:
        return False
    names = {p.name.lower() for p in files}
    if any(p.suffix.lower() != ".webp" for p in files):
        return True
    if "preview.webp" not in names:
        return True
    for p in files:
        stem = p.stem.lower()
        if stem != "preview" and not re.fullmatch(r"gallery_\d{2}", stem):
            return True
    return False


def normalize_folder(folder: Path) -> None:
    files = sorted([p for p in folder.iterdir() if is_image_file(p)], key=natural_sort_key)
    if not files or not needs_normalization(files):
        return

    originals = list(files)
    generated: list[Path] = []
    for idx, src in enumerate(originals):
        name = "preview.webp" if idx == 0 else f"gallery_{idx:02d}.webp"
        dst = folder / name
        convert_image(src, dst)
        generated.append(dst)

    for src in originals:
        if src not in generated and src.exists():
            src.unlink()


def sort_normalized_images(files: list[Path]) -> list[Path]:
    return sorted(files, key=lambda p: (0 if p.name.lower() == "preview.webp" else 1, p.name.lower()))


def build_web_path(article: str, filename: str) -> str:
    return f"/makitaapril_delivery_2026-05-07/import_images/{article}/{filename}"


def build_bitrix_web_path(article: str, filename: str) -> str:
    return f"/upload/vvm_images/import_images/{article}/{filename}"


def main() -> None:
    if not IMAGES_DIR.exists():
        raise FileNotFoundError(f"Images dir not found: {IMAGES_DIR}")

    for folder in sorted([p for p in IMAGES_DIR.iterdir() if p.is_dir()]):
        normalize_folder(folder)

    import_rows: list[dict] = []
    bitrix_rows: list[dict] = []

    for folder in sorted([p for p in IMAGES_DIR.iterdir() if p.is_dir()], key=lambda p: p.name.upper()):
        article = folder.name
        files = sort_normalized_images([p for p in folder.iterdir() if is_image_file(p)])
        if not files:
            continue
        preview = files[0]
        gallery = files[1:]
        import_rows.append(
            {
                ARTICLE_COL: article,
                PREVIEW_COL: build_web_path(article, preview.name),
                MORE_PHOTO_COL: ";".join(build_web_path(article, f.name) for f in gallery),
            }
        )
        bitrix_rows.append(
            {
                ARTICLE_COL: article,
                PREVIEW_COL: build_bitrix_web_path(article, preview.name),
                MORE_PHOTO_COL: ";".join(build_bitrix_web_path(article, f.name) for f in gallery),
            }
        )

    import_df = pd.DataFrame(import_rows, columns=[ARTICLE_COL, PREVIEW_COL, MORE_PHOTO_COL])
    import_df.to_excel(IMPORT_FILE, index=False)

    bitrix_df = pd.DataFrame(bitrix_rows, columns=[ARTICLE_COL, PREVIEW_COL, MORE_PHOTO_COL])
    bitrix_df.to_excel(BITRIX_IMPORT_FILE, index=False)

    print("=== REBUILD IMPORT FROM IMAGES ===")
    print(f"Rows exported: {len(import_df)}")
    print(f"Saved: {IMPORT_FILE}")
    print(f"Saved: {BITRIX_IMPORT_FILE}")


if __name__ == "__main__":
    main()
