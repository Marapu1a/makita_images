from pathlib import Path
import pandas as pd

# =========================
# НАСТРОЙКИ
# =========================
INPUT_FILE = "pictures.xlsx"
OUTPUT_FILE = "pictures_with_links.xlsx"

ARTICLE_COL = "Артикул [ARTIKUL]"
PREVIEW_COL = "Картинка для анонса (путь)"
MORE_PHOTO_COL = "Картинки галереи [MORE_PHOTO]"

BASE_DIR = Path(__file__).resolve().parent

ACCESSORIES_DIR = BASE_DIR / "upload" / "vvm_images" / "accessories"
INSTRUMENTS_DIR = BASE_DIR / "upload" / "vvm_images" / "instruments"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


# =========================
# УТИЛИТЫ
# =========================
def is_image_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def is_empty(value) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def split_more_photo(value) -> list[str]:
    if is_empty(value):
        return []
    return [item.strip() for item in str(value).split(";") if item.strip()]


def merge_more_photo(existing_value, new_value: str) -> tuple[str, int]:
    """
    Возвращает:
    - итоговую строку MORE_PHOTO
    - сколько новых путей реально добавлено
    """
    existing_list = split_more_photo(existing_value)
    new_list = split_more_photo(new_value)

    existing_set = set(existing_list)
    added_count = 0

    for path in new_list:
        if path not in existing_set:
            existing_list.append(path)
            existing_set.add(path)
            added_count += 1

    return ";".join(existing_list), added_count


def find_product_folder(article: str) -> tuple[Path | None, str | None]:
    """
    Ищем папку товара:
    1) accessories/{article}
    2) instruments/{article}
    """
    acc_path = ACCESSORIES_DIR / article
    if acc_path.exists() and acc_path.is_dir():
        return acc_path, "accessories"

    instr_path = INSTRUMENTS_DIR / article
    if instr_path.exists() and instr_path.is_dir():
        return instr_path, "instruments"

    return None, None


def sort_images(files: list[Path]) -> list[Path]:
    """
    Сортировка:
    - preview.* всегда выше
    - остальное по имени файла
    """
    return sorted(
        files,
        key=lambda p: (
            0 if p.stem.lower() == "preview" else 1,
            p.name.lower(),
        )
    )


def build_web_path(category: str, article: str, filename: str) -> str:
    return f"/upload/vvm_images/{category}/{article}/{filename}"


def get_preview_and_gallery(folder: Path, category: str, article: str) -> tuple[str, str, int]:
    """
    Возвращает:
    - preview_path
    - more_photo_path
    - gallery_count (сколько картинок ушло в MORE_PHOTO)
    """
    image_files = [p for p in folder.iterdir() if is_image_file(p)]

    if not image_files:
        return "", "", 0

    image_files = sort_images(image_files)

    preview_file = None
    gallery_files = []

    for f in image_files:
        if f.stem.lower() == "preview":
            preview_file = f
        else:
            gallery_files.append(f)

    if preview_file is None:
        preview_file = image_files[0]
        gallery_files = [f for f in image_files[1:]]

    preview_path = build_web_path(category, article, preview_file.name)
    gallery_paths = [build_web_path(category, article, f.name) for f in gallery_files]

    return preview_path, ";".join(gallery_paths), len(gallery_paths)


# =========================
# ОСНОВНАЯ ЛОГИКА
# =========================
def main():
    input_path = BASE_DIR / INPUT_FILE
    output_path = BASE_DIR / OUTPUT_FILE

    if not input_path.exists():
        raise FileNotFoundError(f"Не найден файл: {input_path}")

    if not ACCESSORIES_DIR.exists():
        raise FileNotFoundError(f"Не найдена папка accessories: {ACCESSORIES_DIR}")

    if not INSTRUMENTS_DIR.exists():
        raise FileNotFoundError(f"Не найдена папка instruments: {INSTRUMENTS_DIR}")

    df = pd.read_excel(input_path)

    if ARTICLE_COL not in df.columns:
        raise ValueError(f"В файле нет колонки: {ARTICLE_COL}")

    if PREVIEW_COL not in df.columns:
        df[PREVIEW_COL] = ""

    if MORE_PHOTO_COL not in df.columns:
        df[MORE_PHOTO_COL] = ""

    total_rows = len(df)

    empty_article_count = 0
    found_total = 0
    found_in_accessories = 0
    found_in_instruments = 0
    not_found_count = 0
    no_images_count = 0

    already_had_preview_count = 0
    already_had_gallery_count = 0

    preview_added_rows = 0
    gallery_added_rows = 0
    untouched_rows = 0

    total_preview_images_added = 0
    total_gallery_images_added = 0

    for idx, row in df.iterrows():
        article = str(row.get(ARTICLE_COL, "")).strip()
        existing_preview = row.get(PREVIEW_COL, "")
        existing_gallery = row.get(MORE_PHOTO_COL, "")

        row_changed = False

        if not is_empty(existing_preview):
            already_had_preview_count += 1

        if not is_empty(existing_gallery):
            already_had_gallery_count += 1

        if not article:
            empty_article_count += 1
            untouched_rows += 1
            continue

        folder, category = find_product_folder(article)

        if folder is None or category is None:
            not_found_count += 1
            untouched_rows += 1
            continue

        found_total += 1
        if category == "accessories":
            found_in_accessories += 1
        elif category == "instruments":
            found_in_instruments += 1

        preview_path, more_photo_path, _ = get_preview_and_gallery(folder, category, article)

        if not preview_path:
            no_images_count += 1
            untouched_rows += 1
            continue

        # ---- PREVIEW: заполняем только если пусто
        if is_empty(existing_preview) and preview_path:
            df.at[idx, PREVIEW_COL] = preview_path
            preview_added_rows += 1
            total_preview_images_added += 1
            row_changed = True

        # ---- MORE_PHOTO: если есть новые пути, добавляем без дублей
        if more_photo_path:
            merged_gallery, added_gallery_count = merge_more_photo(existing_gallery, more_photo_path)

            if added_gallery_count > 0:
                df.at[idx, MORE_PHOTO_COL] = merged_gallery
                gallery_added_rows += 1
                total_gallery_images_added += added_gallery_count
                row_changed = True

        if not row_changed:
            untouched_rows += 1

    df.to_excel(output_path, index=False)

    total_images_added = total_preview_images_added + total_gallery_images_added

    print("\n=== ОБРАБОТКА КАРТИНОК MAKITA ===")
    print(f"Всего строк в Excel: {total_rows}")
    print(f"Пустой артикул: {empty_article_count}")
    print(f"Папка товара найдена: {found_total}")
    print(f"  - accessories: {found_in_accessories}")
    print(f"  - instruments: {found_in_instruments}")
    print(f"Папка товара не найдена: {not_found_count}")
    print(f"Папка найдена, но картинок нет: {no_images_count}")

    print("\n=== ЧТО УЖЕ БЫЛО В ФАЙЛЕ ===")
    print(f"Строк уже с preview: {already_had_preview_count}")
    print(f"Строк уже с [MORE_PHOTO]: {already_had_gallery_count}")

    print("\n=== ЧТО ДОБАВЛЕНО СКРИПТОМ ===")
    print(f"Строк, где добавлен preview: {preview_added_rows}")
    print(f"Строк, где добавлены пути в [MORE_PHOTO]: {gallery_added_rows}")

    print("\n=== ДОБАВЛЕНО КАРТИНОК ===")
    print(f"Preview-картинок добавлено: {total_preview_images_added}")
    print(f"Галерейных картинок добавлено: {total_gallery_images_added}")
    print(f"Всего новых путей к картинкам добавлено: {total_images_added}")

    print("\n=== ИТОГ ПО СТРОКАМ ===")
    print(f"Строк не изменено: {untouched_rows}")

    print("\nСохранено:")
    print(f"- {output_path.name}")


if __name__ == "__main__":
    main()