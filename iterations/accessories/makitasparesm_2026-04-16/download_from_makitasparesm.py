from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, quote_plus
import re
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "input" / "pictures.xlsx"
OUTPUT_DIR = BASE_DIR / "output" / "import_images"
REPORT_FILE = BASE_DIR / "output" / "makitasparesm_report.xlsx"

BASE_URL = "https://www.makitasparesm.com"
SEARCH_URL = BASE_URL + "/?s={query}&post_type=product"
SOURCE_NAME = "makitasparesm.com"

COL_ARTICLE = "Артикул [ARTIKUL]"
COL_NAME = "Наименование элемента"

REQUEST_TIMEOUT = 40
FETCH_RETRIES = 2
DOWNLOAD_RETRIES = 2
RETRY_SLEEP = 0.5
SLEEP_BETWEEN_ITEMS = 0.15
MIN_BYTES = 1000

WEBP_QUALITY = 82
WEBP_METHOD = 6
MAX_WIDTH = 1600
MAX_HEIGHT = 1600

Image.MAX_IMAGE_PIXELS = None
SAVE_EVERY = 25


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


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/135.0.0.0 Safari/537.36"
            )
        }
    )
    return session


def fetch_text(url: str, session: requests.Session) -> str:
    last_error = None
    for _ in range(FETCH_RETRIES + 1):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text
        except Exception as exc:
            last_error = exc
            time.sleep(RETRY_SLEEP)
    raise last_error


def search_product(article: str, session: requests.Session) -> tuple[str | None, str]:
    search_url = SEARCH_URL.format(query=quote_plus(article))
    text = fetch_text(search_url, session)
    soup = BeautifulSoup(text, "html.parser")

    article_token = normalize_token(article)
    candidates: list[tuple[str, str]] = []

    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()
        if "/product/" not in href:
            continue
        href = href.split("#")[0]
        title = " ".join(a.get_text(" ", strip=True).split())
        if not href:
            continue
        token_source = f"{href} {title}"
        if article_token in normalize_token(token_source):
            candidates.append((urljoin(BASE_URL, href), title))

    seen = set()
    deduped: list[tuple[str, str]] = []
    for href, title in candidates:
        if href in seen:
            continue
        seen.add(href)
        deduped.append((href, title))

    if not deduped:
        return None, ""

    return deduped[0]


def extract_product_data(article: str, product_url: str, session: requests.Session) -> tuple[str, list[str], str]:
    text = fetch_text(product_url, session)
    soup = BeautifulSoup(text, "html.parser")

    title_node = soup.select_one(".product_title, h1")
    title = " ".join(title_node.get_text(" ", strip=True).split()) if title_node else ""
    token_source = f"{product_url} {title}"

    if normalize_token(article) not in normalize_token(token_source):
        return title, [], "article_mismatch"

    image_urls: list[str] = []
    for img in soup.select(".woocommerce-product-gallery img[src], .woocommerce-product-gallery img[data-src]"):
        src = img.get("data-src") or img.get("src") or ""
        if not src:
            continue
        full_url = urljoin(BASE_URL, src)
        if "/wp-content/uploads/" not in full_url.lower():
            continue
        alt = " ".join((img.get("alt") or "").split())
        if normalize_token(article) not in normalize_token(f"{full_url} {alt}"):
            continue
        if full_url not in image_urls:
            image_urls.append(full_url)

    if not image_urls:
        raw_urls = re.findall(r'https://[^"\']+\.(?:jpg|jpeg|png|webp)', text, flags=re.I)
        for image_url in raw_urls:
            if "/wp-content/uploads/" not in image_url.lower():
                continue
            if normalize_token(article) not in normalize_token(image_url):
                continue
            if image_url not in image_urls:
                image_urls.append(image_url)

    if not image_urls:
        return title, [], "no_matching_images"

    return title, image_urls[:1], "ok"


def prepare_image_for_webp(image: Image.Image) -> Image.Image:
    has_alpha = image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)
    image = image.convert("RGBA" if has_alpha else "RGB")
    image.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.LANCZOS)
    return image


def download_and_compress_image(url: str, target_path: Path, session: requests.Session) -> tuple[bool, str]:
    last_reason = "unknown"

    for _ in range(DOWNLOAD_RETRIES + 1):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
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


def save_product_images(article: str, image_urls: list[str], session: requests.Session) -> tuple[bool, int, str]:
    if not image_urls:
        return False, 0, "no_images"

    item_dir = OUTPUT_DIR / safe_name(article)
    item_dir.mkdir(parents=True, exist_ok=True)

    ok, note = download_and_compress_image(image_urls[0], item_dir / "preview.webp", session)
    if ok:
        return True, 0, "ok"
    return False, 0, f"preview_failed:{note}"


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

    names = {}
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

        rows.append(
            {
                "article": article,
                "name": names.get(article, ""),
                "source_name": SOURCE_NAME,
                "search_url": SEARCH_URL.format(query=quote_plus(article)),
                "product_url": "",
                "status": "OK",
                "images_found": 1,
                "gallery_saved": 0,
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

    ok_count = sum(1 for row in report_rows if row.get("status") == "OK")
    fail_count = sum(1 for row in report_rows if row.get("status") == "FAIL")

    with make_session() as session:
        total = len(df)

        for index, row in df.iterrows():
            article = str(row.get(COL_ARTICLE, "")).strip()
            name = str(row.get(COL_NAME, "")).strip()
            article_norm = normalize_article(article)

            if article_norm in processed_articles:
                continue

            print(f"[{index + 1}/{total}] {article} | {name}")

            if not article:
                fail_count += 1
                report_rows.append(
                    {
                        "article": article,
                        "name": name,
                        "source_name": SOURCE_NAME,
                        "search_url": "",
                        "product_url": "",
                        "status": "FAIL",
                        "images_found": 0,
                        "gallery_saved": 0,
                        "note": "empty_article",
                    }
                )
                processed_articles.add(article_norm)
                if len(report_rows) % SAVE_EVERY == 0:
                    pd.DataFrame(report_rows).to_excel(REPORT_FILE, index=False)
                continue

            search_url = SEARCH_URL.format(query=quote_plus(article))

            try:
                product_url, found_title = search_product(article, session)
            except Exception as exc:
                fail_count += 1
                report_rows.append(
                    {
                        "article": article,
                        "name": name,
                        "source_name": SOURCE_NAME,
                        "search_url": search_url,
                        "product_url": "",
                        "status": "FAIL",
                        "images_found": 0,
                        "gallery_saved": 0,
                        "note": f"search_error:{exc}",
                    }
                )
                processed_articles.add(article_norm)
                if len(report_rows) % SAVE_EVERY == 0:
                    pd.DataFrame(report_rows).to_excel(REPORT_FILE, index=False)
                time.sleep(SLEEP_BETWEEN_ITEMS)
                continue

            if not product_url:
                fail_count += 1
                report_rows.append(
                    {
                        "article": article,
                        "name": name,
                        "source_name": SOURCE_NAME,
                        "search_url": search_url,
                        "product_url": "",
                        "status": "FAIL",
                        "images_found": 0,
                        "gallery_saved": 0,
                        "note": "product_not_found",
                    }
                )
                processed_articles.add(article_norm)
                if len(report_rows) % SAVE_EVERY == 0:
                    pd.DataFrame(report_rows).to_excel(REPORT_FILE, index=False)
                time.sleep(SLEEP_BETWEEN_ITEMS)
                continue

            try:
                product_title, image_urls, note = extract_product_data(article, product_url, session)
            except Exception as exc:
                fail_count += 1
                report_rows.append(
                    {
                        "article": article,
                        "name": name,
                        "source_name": SOURCE_NAME,
                        "search_url": search_url,
                        "product_url": product_url,
                        "status": "FAIL",
                        "images_found": 0,
                        "gallery_saved": 0,
                        "note": f"product_parse_error:{exc}",
                    }
                )
                processed_articles.add(article_norm)
                if len(report_rows) % SAVE_EVERY == 0:
                    pd.DataFrame(report_rows).to_excel(REPORT_FILE, index=False)
                time.sleep(SLEEP_BETWEEN_ITEMS)
                continue

            if not image_urls:
                fail_count += 1
                report_rows.append(
                    {
                        "article": article,
                        "name": name,
                        "source_name": SOURCE_NAME,
                        "search_url": search_url,
                        "product_url": product_url,
                        "status": "FAIL",
                        "images_found": 0,
                        "gallery_saved": 0,
                        "note": note,
                    }
                )
                time.sleep(SLEEP_BETWEEN_ITEMS)
                continue

            ok, gallery_saved, save_note = save_product_images(article, image_urls, session)
            status = "OK" if ok else "FAIL"
            if ok:
                ok_count += 1
            else:
                fail_count += 1

            report_rows.append(
                {
                    "article": article,
                    "name": name,
                    "source_name": SOURCE_NAME,
                    "search_url": search_url,
                    "product_url": product_url,
                    "status": status,
                    "images_found": len(image_urls),
                    "gallery_saved": gallery_saved,
                    "note": save_note if ok else f"{note};{save_note}",
                }
            )
            processed_articles.add(article_norm)
            if len(report_rows) % SAVE_EVERY == 0:
                pd.DataFrame(report_rows).to_excel(REPORT_FILE, index=False)

            time.sleep(SLEEP_BETWEEN_ITEMS)

    report_df = pd.DataFrame(report_rows)
    report_df.to_excel(REPORT_FILE, index=False)

    print("\n=== MAKITASPARESM DOWNLOAD SUMMARY ===")
    print(f"Input rows: {len(df)}")
    print(f"OK: {ok_count}")
    print(f"FAIL: {fail_count}")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
