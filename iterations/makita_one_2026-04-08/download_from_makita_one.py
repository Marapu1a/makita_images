from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.parse import quote_plus, urljoin
import re
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "input" / "pictures.xlsx"
OUTPUT_DIR = BASE_DIR / "output" / "import_images"
REPORT_FILE = BASE_DIR / "output" / "makita_one_report.xlsx"

BASE_URL = "https://makita.one"
SEARCH_URL = BASE_URL + "/catalog/?q={query}&s=%D0%9D%D0%B0%D0%B9%D1%82%D0%B8"
SOURCE_NAME = "makita.one"

COL_ARTICLE = "Артикул [ARTIKUL]"
COL_NAME = "Наименование элемента"

REQUEST_TIMEOUT = 30
FETCH_RETRIES = 2
DOWNLOAD_RETRIES = 2
RETRY_SLEEP = 0.5
SLEEP_BETWEEN_ITEMS = 0.2
MAX_GALLERY = 5
MIN_BYTES = 1000

WEBP_QUALITY = 82
WEBP_METHOD = 6
MAX_WIDTH = 1600
MAX_HEIGHT = 1600

Image.MAX_IMAGE_PIXELS = None


def is_empty(value) -> bool:
    if pd.isna(value):
        return True
    text = str(value).strip()
    return text == "" or text.lower() == "nan"


def normalize_article(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().upper()
    return re.sub(r"\s+", "", text)


def safe_name(value: object) -> str:
    text = str(value).strip()
    text = re.sub(r"[^\w\-.]+", "_", text)
    return text[:120]


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
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


def search_exact_product(article: str, session: requests.Session) -> tuple[str | None, str]:
    search_url = SEARCH_URL.format(query=quote_plus(article))
    text = fetch_text(search_url, session)
    soup = BeautifulSoup(text, "html.parser")

    article_norm = normalize_article(article)
    cards = soup.select("div.item_block")

    for card in cards:
        article_block = card.select_one(".article_block")
        title_link = card.select_one("a.dark_link[href]")

        if not article_block or not title_link:
            continue

        card_article = normalize_article(article_block.get("data-value", ""))
        if card_article != article_norm:
            continue

        href = title_link.get("href", "").strip()
        if not href:
            continue

        title = " ".join(title_link.get_text(" ", strip=True).split())
        return urljoin(BASE_URL, href), title

    return None, ""


def extract_product_data(product_url: str, session: requests.Session) -> tuple[str, str, list[str]]:
    text = fetch_text(product_url, session)
    soup = BeautifulSoup(text, "html.parser")

    title_node = soup.select_one("h1#pagetitle")
    title = " ".join(title_node.get_text(" ", strip=True).split()) if title_node else ""

    article_node = soup.select_one(".article__value, .article_block[data-value]")
    article = ""
    if article_node:
        article = (article_node.get("data-value") or article_node.get_text(" ", strip=True)).strip()

    image_urls: list[str] = []

    for node in soup.select(".gallery__item--thumb[data-big]"):
        image_url = node.get("data-big", "").strip()
        if not image_url:
            continue
        full_url = urljoin(BASE_URL, image_url)
        if full_url not in image_urls:
            image_urls.append(full_url)

    if not image_urls:
        raw_iblock = re.findall(
            r"/upload/iblock/[^\"'\s<>]+\.(?:jpg|jpeg|png|webp)",
            text,
            flags=re.I,
        )
        for image_url in raw_iblock:
            lower = image_url.lower()
            if "logo" in lower:
                continue
            full_url = urljoin(BASE_URL, image_url)
            if full_url not in image_urls:
                image_urls.append(full_url)

    return title, article, image_urls


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

    saved_preview = False
    saved_gallery = 0
    fail_reason = ""

    preview_ok, preview_reason = download_and_compress_image(image_urls[0], item_dir / "preview.webp", session)
    if preview_ok:
        saved_preview = True
    else:
        fail_reason = f"preview_failed:{preview_reason}"

    for image_url in image_urls[1 : 1 + MAX_GALLERY]:
        gallery_path = item_dir / f"gallery_{saved_gallery + 1:02}.webp"
        ok, _ = download_and_compress_image(image_url, gallery_path, session)
        if ok:
            saved_gallery += 1

    if saved_preview or saved_gallery > 0:
        return True, saved_gallery, "ok"

    return False, 0, fail_reason or "download_failed"


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(INPUT_FILE)

    required_columns = [COL_ARTICLE, COL_NAME]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    report_rows: list[dict] = []

    ok_count = 0
    fail_count = 0
    skip_count = 0

    with make_session() as session:
        total = len(df)

        for index, row in df.iterrows():
            article = str(row.get(COL_ARTICLE, "")).strip()
            name = str(row.get(COL_NAME, "")).strip()

            print(f"[{index + 1}/{total}] {article} | {name}")

            if is_empty(article):
                skip_count += 1
                report_rows.append(
                    {
                        "article": article,
                        "name": name,
                        "source_name": SOURCE_NAME,
                        "search_url": "",
                        "product_url": "",
                        "found_article": "",
                        "status": "SKIP",
                        "images_found": 0,
                        "gallery_saved": 0,
                        "note": "empty_article",
                    }
                )
                continue

            search_url = SEARCH_URL.format(query=quote_plus(article))

            try:
                product_url, found_title = search_exact_product(article, session)
            except Exception as exc:
                fail_count += 1
                report_rows.append(
                    {
                        "article": article,
                        "name": name,
                        "source_name": SOURCE_NAME,
                        "search_url": search_url,
                        "product_url": "",
                        "found_article": "",
                        "status": "FAIL",
                        "images_found": 0,
                        "gallery_saved": 0,
                        "note": f"search_error:{exc}",
                    }
                )
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
                        "found_article": "",
                        "status": "FAIL",
                        "images_found": 0,
                        "gallery_saved": 0,
                        "note": "product_not_found",
                    }
                )
                time.sleep(SLEEP_BETWEEN_ITEMS)
                continue

            try:
                product_title, found_article, image_urls = extract_product_data(product_url, session)
            except Exception as exc:
                fail_count += 1
                report_rows.append(
                    {
                        "article": article,
                        "name": name,
                        "source_name": SOURCE_NAME,
                        "search_url": search_url,
                        "product_url": product_url,
                        "found_article": "",
                        "status": "FAIL",
                        "images_found": 0,
                        "gallery_saved": 0,
                        "note": f"product_parse_error:{exc}",
                    }
                )
                continue

            if normalize_article(found_article) != normalize_article(article):
                fail_count += 1
                report_rows.append(
                    {
                        "article": article,
                        "name": name,
                        "source_name": SOURCE_NAME,
                        "search_url": search_url,
                        "product_url": product_url,
                        "found_article": found_article,
                        "status": "FAIL",
                        "images_found": len(image_urls),
                        "gallery_saved": 0,
                        "note": "article_mismatch",
                    }
                )
                time.sleep(SLEEP_BETWEEN_ITEMS)
                continue

            ok, gallery_saved, note = save_product_images(article, image_urls, session)
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
                    "found_article": found_article,
                    "status": status,
                    "images_found": len(image_urls),
                    "gallery_saved": gallery_saved,
                    "note": note,
                }
            )

            time.sleep(SLEEP_BETWEEN_ITEMS)

    report_df = pd.DataFrame(report_rows)
    report_df.to_excel(REPORT_FILE, index=False)

    print("\n=== MAKITA.ONE DOWNLOAD SUMMARY ===")
    print(f"Input rows: {len(df)}")
    print(f"OK: {ok_count}")
    print(f"FAIL: {fail_count}")
    print(f"SKIP: {skip_count}")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
