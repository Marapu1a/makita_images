from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.parse import quote_plus, urljoin
import re
import time

import cloudscraper
import pandas as pd
from bs4 import BeautifulSoup
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "input" / "pictures.xlsx"
OUTPUT_DIR = BASE_DIR / "output" / "import_images"
REPORT_FILE = BASE_DIR / "output" / "makita_ae_report.xlsx"

BASE_URL = "https://makita.ae"
SEARCH_URL = BASE_URL + "/?s={query}&post_type=product"
SOURCE_NAME = "makita.ae"

COL_ARTICLE = "Артикул [ARTIKUL]"
COL_NAME = "Наименование элемента"

REQUEST_TIMEOUT = 40
FETCH_RETRIES = 2
DOWNLOAD_RETRIES = 2
RETRY_SLEEP = 0.7
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


def normalize_token(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", value.upper())


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


def fetch_text(url: str, scraper: cloudscraper.CloudScraper) -> str:
    last_error = None
    for _ in range(FETCH_RETRIES + 1):
        try:
            response = scraper.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text
        except Exception as exc:
            last_error = exc
            time.sleep(RETRY_SLEEP)
    raise last_error


def search_product(article: str, scraper: cloudscraper.CloudScraper) -> tuple[str | None, str]:
    url = SEARCH_URL.format(query=quote_plus(article))
    text = fetch_text(url, scraper)
    soup = BeautifulSoup(text, "html.parser")
    article_token = normalize_token(article)

    candidates: list[tuple[str, str]] = []
    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()
        if "/product/" not in href:
            continue
        title = " ".join(a.get_text(" ", strip=True).split())
        full_url = urljoin(BASE_URL, href)
        blob = normalize_token(f"{full_url} {title}")
        if article_token in blob:
            candidates.append((full_url, title))

    seen = set()
    deduped = []
    for url_value, title in candidates:
        if url_value in seen:
            continue
        seen.add(url_value)
        deduped.append((url_value, title))

    if deduped:
        return deduped[0]
    return None, ""


def canonicalize_image_url(url: str) -> str:
    return re.sub(r"-\d+x\d+(?=\.[a-z0-9]+$)", "", url, flags=re.I)


def extract_product_data(article: str, product_url: str, scraper: cloudscraper.CloudScraper) -> tuple[str, list[str], str]:
    text = fetch_text(product_url, scraper)
    article_token = normalize_token(article)
    if article_token not in normalize_token(text):
        return "", [], "article_not_in_page"

    soup = BeautifulSoup(text, "html.parser")
    image_urls: list[str] = []

    for img in soup.select(".woocommerce-product-gallery img[src], .woocommerce-product-gallery img[data-src], meta[property='og:image']"):
        src = img.get("data-src") or img.get("src") or img.get("content") or ""
        if not src:
            continue
        full_url = urljoin(BASE_URL, src.strip())
        if "/wp-content/uploads/" not in full_url.lower():
            continue
        full_url = canonicalize_image_url(full_url)
        if article_token not in normalize_token(full_url):
            continue
        if full_url not in image_urls:
            image_urls.append(full_url)

    if not image_urls:
        raw_urls = re.findall(r'https://[^"\']+\.(?:jpg|jpeg|png|webp)', text, flags=re.I)
        for image_url in raw_urls:
            if "/wp-content/uploads/" not in image_url.lower():
                continue
            image_url = canonicalize_image_url(image_url)
            if article_token not in normalize_token(image_url):
                continue
            if image_url not in image_urls:
                image_urls.append(image_url)

    if not image_urls:
        return "", [], "no_matching_images"

    return product_url, image_urls[: 1 + MAX_GALLERY], "ok"


def prepare_image_for_webp(image: Image.Image) -> Image.Image:
    has_alpha = image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)
    image = image.convert("RGBA" if has_alpha else "RGB")
    image.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.LANCZOS)
    return image


def download_and_compress_image(url: str, target_path: Path, scraper: cloudscraper.CloudScraper) -> tuple[bool, str]:
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


def save_product_images(article: str, image_urls: list[str], scraper: cloudscraper.CloudScraper) -> tuple[bool, int, str]:
    if not image_urls:
        return False, 0, "no_images"
    item_dir = OUTPUT_DIR / safe_name(article)
    item_dir.mkdir(parents=True, exist_ok=True)
    preview_ok, note = download_and_compress_image(image_urls[0], item_dir / "preview.webp", scraper)
    if not preview_ok:
        return False, 0, f"preview_failed:{note}"
    gallery_saved = 0
    for image_url in image_urls[1:]:
        gallery_path = item_dir / f"gallery_{gallery_saved + 1:02}.webp"
        ok, _ = download_and_compress_image(image_url, gallery_path, scraper)
        if ok:
            gallery_saved += 1
    return True, gallery_saved, "ok"


def load_existing_report() -> tuple[list[dict], set[str]]:
    if not REPORT_FILE.exists():
        return [], set()
    df = pd.read_excel(REPORT_FILE)
    rows = df.to_dict(orient="records")
    processed = {normalize_article(row.get("article")) for row in rows if normalize_article(row.get("article"))}
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
    df = pd.read_excel(INPUT_FILE)
    report_rows, processed_articles = load_existing_report()
    if not report_rows:
        existing_rows, existing_processed = build_existing_folder_rows(df)
        report_rows.extend(existing_rows)
        processed_articles |= existing_processed

    ok_count = sum(1 for row in report_rows if row.get("status") == "OK")
    fail_count = sum(1 for row in report_rows if row.get("status") == "FAIL")
    scraper = make_scraper()

    total = len(df)
    for index, row in df.iterrows():
        article = str(row.get(COL_ARTICLE, "")).strip()
        name = str(row.get(COL_NAME, "")).strip()
        article_norm = normalize_article(article)

        if article_norm in processed_articles:
            continue

        print(f"[{index + 1}/{total}] {safe_console_text(article)} | {safe_console_text(name)}")

        try:
            product_url, _ = search_product(article_norm, scraper)
            if not product_url:
                raise ValueError("product_not_found")
            product_url, image_urls, note = extract_product_data(article_norm, product_url, scraper)
            if note != "ok":
                raise ValueError(note)
            saved_ok, gallery_saved, save_note = save_product_images(article_norm, image_urls, scraper)
            if not saved_ok:
                raise ValueError(save_note)
            ok_count += 1
            report_rows.append(
                {
                    "article": article_norm,
                    "name": name,
                    "source_name": SOURCE_NAME,
                    "product_url": product_url,
                    "status": "OK",
                    "images_found": len(image_urls),
                    "gallery_saved": gallery_saved,
                    "note": "ok",
                }
            )
            print(f"  -> OK | OK={ok_count} FAIL={fail_count}")
        except Exception as exc:
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
                    "note": str(exc).strip() or type(exc).__name__,
                }
            )

        processed_articles.add(article_norm)
        if len(report_rows) % SAVE_EVERY == 0:
            pd.DataFrame(report_rows).to_excel(REPORT_FILE, index=False)
        time.sleep(SLEEP_BETWEEN_ITEMS)

    pd.DataFrame(report_rows).to_excel(REPORT_FILE, index=False)
    print(f"Done. Report saved to: {REPORT_FILE}")


if __name__ == "__main__":
    main()
