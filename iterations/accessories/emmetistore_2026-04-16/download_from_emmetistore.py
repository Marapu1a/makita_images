from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import time

import cloudscraper
import pandas as pd
import requests
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "input" / "pictures.xlsx"
OUTPUT_DIR = BASE_DIR / "output" / "import_images"
REPORT_FILE = BASE_DIR / "output" / "emmetistore_report.xlsx"

BASE_URL = "https://www.emmetistore.com"
COLLECTION_PRODUCTS_URL = BASE_URL + "/collections/makita/products.json?limit=250&page={page}"
SOURCE_NAME = "emmetistore.com"

COL_ARTICLE = "Артикул [ARTIKUL]"
COL_NAME = "Наименование элемента"

REQUEST_TIMEOUT = 40
RETRY_SLEEP = 0.7
DOWNLOAD_RETRIES = 2
SLEEP_BETWEEN_ITEMS = 0.15
SAVE_EVERY = 25
MIN_BYTES = 1000
MAX_GALLERY = 5

WEBP_QUALITY = 82
WEBP_METHOD = 6
MAX_WIDTH = 1600
MAX_HEIGHT = 1600

Image.MAX_IMAGE_PIXELS = None


def normalize_article(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().upper()


def safe_name(value: object) -> str:
    text = str(value).strip()
    text = re.sub(r"[^\w\-.]+", "_", text)
    return text[:120]


def safe_console_text(value: object) -> str:
    return str(value).encode("cp1251", errors="replace").decode("cp1251", errors="replace")


def make_scraper() -> cloudscraper.CloudScraper:
    return cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )


def fetch_collection_products(scraper: cloudscraper.CloudScraper) -> list[dict]:
    products: list[dict] = []
    page = 1

    while True:
        url = COLLECTION_PRODUCTS_URL.format(page=page)
        response = scraper.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        batch = response.json().get("products", [])
        if not batch:
            break
        products.extend(batch)
        page += 1
        time.sleep(0.1)

    return products


def build_sku_map(products: list[dict]) -> dict[str, dict]:
    sku_map: dict[str, dict] = {}
    for product in products:
        for variant in product.get("variants", []):
            sku = normalize_article(variant.get("sku"))
            if sku and sku not in sku_map:
                sku_map[sku] = product
    return sku_map


def prepare_image_for_webp(image: Image.Image) -> Image.Image:
    has_alpha = image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)
    image = image.convert("RGBA" if has_alpha else "RGB")
    image.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.LANCZOS)
    return image


def image_url_from_entry(image_entry: dict) -> str:
    url = str(image_entry.get("src") or "").strip()
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return BASE_URL + url
    return url


def download_and_compress_image(
    url: str, target_path: Path, scraper: cloudscraper.CloudScraper
) -> tuple[bool, str]:
    last_reason = "unknown"

    for _ in range(DOWNLOAD_RETRIES + 1):
        try:
            response = scraper.get(url, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                last_reason = f"http_{response.status_code}"
                raise ValueError(last_reason)

            if len(response.content) < MIN_BYTES:
                last_reason = "too_small"
                raise ValueError(last_reason)

            image = Image.open(BytesIO(response.content))
            image = prepare_image_for_webp(image)
            image.save(target_path, format="WEBP", quality=WEBP_QUALITY, method=WEBP_METHOD)
            return True, "ok"
        except Exception as exc:
            if str(exc).strip():
                last_reason = str(exc).strip()
            time.sleep(RETRY_SLEEP)

    return False, last_reason


def save_product_images(
    article: str, product: dict, scraper: cloudscraper.CloudScraper
) -> tuple[bool, int, int, str]:
    image_entries = product.get("images", [])
    image_urls = [image_url_from_entry(entry) for entry in image_entries]
    image_urls = [url for url in image_urls if url]

    if not image_urls:
        return False, 0, 0, "no_images"

    item_dir = OUTPUT_DIR / safe_name(article)
    item_dir.mkdir(parents=True, exist_ok=True)

    saved_preview = False
    saved_gallery = 0

    ok, note = download_and_compress_image(image_urls[0], item_dir / "preview.webp", scraper)
    if ok:
        saved_preview = True
    else:
        return False, 0, 0, f"preview_failed:{note}"

    for image_url in image_urls[1 : 1 + MAX_GALLERY]:
        gallery_path = item_dir / f"gallery_{saved_gallery + 1:02}.webp"
        gallery_ok, _ = download_and_compress_image(image_url, gallery_path, scraper)
        if gallery_ok:
            saved_gallery += 1

    return saved_preview or saved_gallery > 0, len(image_urls), saved_gallery, "ok"


def load_existing_report() -> tuple[list[dict], set[str]]:
    if not REPORT_FILE.exists():
        return [], set()

    df = pd.read_excel(REPORT_FILE)
    rows = df.to_dict(orient="records")
    processed = {
        normalize_article(row.get("article"))
        for row in rows
        if normalize_article(row.get("article"))
    }
    return rows, processed


def build_existing_folder_rows(df: pd.DataFrame) -> tuple[list[dict], set[str]]:
    rows: list[dict] = []
    processed: set[str] = set()

    if not OUTPUT_DIR.exists():
        return rows, processed

    names: dict[str, str] = {}
    for _, row in df.iterrows():
        article = normalize_article(row.get(COL_ARTICLE, ""))
        if article and article not in names:
            names[article] = str(row.get(COL_NAME, "")).strip()

    for folder in OUTPUT_DIR.iterdir():
        if not folder.is_dir() or not (folder / "preview.webp").exists():
            continue

        article = normalize_article(folder.name)
        if not article:
            continue

        gallery_saved = len(list(folder.glob("gallery_*.webp")))
        rows.append(
            {
                "article": article,
                "name": names.get(article, ""),
                "source_name": SOURCE_NAME,
                "product_url": "",
                "status": "OK",
                "images_found": gallery_saved + 1,
                "gallery_saved": gallery_saved,
                "note": "existing_folder_resumed",
            }
        )
        processed.add(article)

    return rows, processed


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(INPUT_FILE)

    required_columns = [COL_ARTICLE, COL_NAME]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    report_rows, processed_articles = load_existing_report()
    if not report_rows:
        existing_rows, existing_processed = build_existing_folder_rows(df)
        report_rows.extend(existing_rows)
        processed_articles |= existing_processed

    scraper = make_scraper()
    products = fetch_collection_products(scraper)
    sku_map = build_sku_map(products)

    total = len(df)
    ok_count = sum(1 for row in report_rows if row.get("status") == "OK")
    fail_count = sum(1 for row in report_rows if row.get("status") == "FAIL")

    print(f"Loaded {len(products)} Makita products and {len(sku_map)} unique SKUs")

    for index, row in df.iterrows():
        article = str(row.get(COL_ARTICLE, "")).strip()
        name = str(row.get(COL_NAME, "")).strip()
        article_norm = normalize_article(article)

        if article_norm in processed_articles:
            continue

        print(f"[{index + 1}/{total}] {safe_console_text(article)} | {safe_console_text(name)}")

        if not article_norm:
            fail_count += 1
            report_rows.append(
                {
                    "article": article,
                    "name": name,
                    "source_name": SOURCE_NAME,
                    "product_url": "",
                    "status": "FAIL",
                    "images_found": 0,
                    "gallery_saved": 0,
                    "note": "empty_article",
                }
            )
            processed_articles.add(article_norm)
            continue

        product = sku_map.get(article_norm)
        if not product:
            fail_count += 1
            report_rows.append(
                {
                    "article": article_norm,
                    "name": name,
                    "source_name": SOURCE_NAME,
                    "product_url": "",
                    "status": "FAIL",
                    "images_found": 0,
                    "gallery_saved": 0,
                    "note": "exact_sku_not_found",
                }
            )
            processed_articles.add(article_norm)
            if len(report_rows) % SAVE_EVERY == 0:
                pd.DataFrame(report_rows).to_excel(REPORT_FILE, index=False)
            continue

        product_url = BASE_URL + "/products/" + str(product.get("handle", "")).strip()

        try:
            ok, images_found, gallery_saved, note = save_product_images(article_norm, product, scraper)
            status = "OK" if ok else "FAIL"
        except Exception as exc:
            ok = False
            status = "FAIL"
            images_found = 0
            gallery_saved = 0
            note = f"save_error:{type(exc).__name__}"

        if ok:
            ok_count += 1
        else:
            fail_count += 1

        report_rows.append(
            {
                "article": article_norm,
                "name": name,
                "source_name": SOURCE_NAME,
                "product_url": product_url,
                "status": status,
                "images_found": images_found,
                "gallery_saved": gallery_saved,
                "note": note,
            }
        )
        processed_articles.add(article_norm)

        if len(report_rows) % SAVE_EVERY == 0:
            pd.DataFrame(report_rows).to_excel(REPORT_FILE, index=False)

        print(f"  -> {status} | OK={ok_count} FAIL={fail_count}")
        time.sleep(SLEEP_BETWEEN_ITEMS)

    pd.DataFrame(report_rows).to_excel(REPORT_FILE, index=False)
    print(f"Done. Report saved to: {REPORT_FILE}")


if __name__ == "__main__":
    main()
