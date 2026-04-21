from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "input" / "pictures.xlsx"
OUTPUT_DIR = BASE_DIR / "output" / "import_images"
REPORT_FILE = BASE_DIR / "output" / "gama_alati_report.xlsx"

BASE_URL = "https://www.gama-alati.rs"
SITEMAP_URL = BASE_URL + "/pub/product_sitemap_1.xml"
SOURCE_NAME = "gama-alati.rs"

COL_ARTICLE = "Артикул [ARTIKUL]"
COL_NAME = "Наименование элемента"

REQUEST_TIMEOUT = 35
FETCH_RETRIES = 2
DOWNLOAD_RETRIES = 2
RETRY_SLEEP = 0.5
SLEEP_BETWEEN_ITEMS = 0.05
SAVE_EVERY = 25
MIN_BYTES = 1200

WEBP_QUALITY = 82
WEBP_METHOD = 6
MAX_WIDTH = 1800
MAX_HEIGHT = 1800

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


def build_sitemap_map(articles: list[str], session: requests.Session) -> dict[str, str]:
    xml = fetch_text(SITEMAP_URL, session)
    resolved: dict[str, str] = {}
    for article in articles:
        match = re.search(rf"<loc>([^<]*{re.escape(article.lower())}[^<]*)</loc>", xml, re.I)
        if match:
            resolved[article] = match.group(1).strip()
    return resolved


def image_sort_key(url: str) -> tuple[int, int, str]:
    lower = url.lower()
    penalty = 0
    if "cache/662cbfff" in lower:
        penalty -= 2
    if "cache/8dbc024e" in lower:
        penalty -= 1
    if "logo" in lower or "placeholder" in lower:
        penalty += 20
    return (penalty, len(url), url)


def extract_product_data(article: str, product_url: str, session: requests.Session) -> tuple[str, list[str], str]:
    text = fetch_text(product_url, session)
    if normalize_token(article) not in normalize_token(text):
        return product_url, [], "article_not_in_page"

    soup = BeautifulSoup(text, "html.parser")
    image_urls: list[str] = []
    for node in soup.select("meta[property='og:image'], img[src], img[data-src]"):
        value = node.get("content") or node.get("data-src") or node.get("src") or ""
        if not value:
            continue
        if value.startswith("/"):
            value = BASE_URL + value
        lower = value.lower()
        if "/media/catalog/product/" not in lower:
            continue
        if "placeholder" in lower or "logo" in lower:
            continue
        if value not in image_urls:
            image_urls.append(value)

    image_urls.sort(key=image_sort_key)
    if not image_urls:
        return product_url, [], "no_real_image"

    return product_url, image_urls[:1], "ok"


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

    preview_ok, note = download_and_compress_image(image_urls[0], item_dir / "preview.webp", session)
    if not preview_ok:
        return False, 0, f"preview_failed:{note}"

    return True, 0, "ok"


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
        rows.append(
            {
                "article": article,
                "name": names.get(article, ""),
                "source_name": SOURCE_NAME,
                "product_url": "",
                "status": "OK",
                "images_found": 1,
                "gallery_saved": 0,
                "note": "existing_folder_resumed",
            }
        )
        processed.add(article)
    return rows, processed


def save_report(rows: list[dict]) -> None:
    pd.DataFrame(rows).to_excel(REPORT_FILE, index=False)


def main() -> None:
    df = pd.read_excel(INPUT_FILE)
    report_rows, processed_articles = load_existing_report()
    if not report_rows:
        existing_rows, existing_processed = build_existing_folder_rows(df)
        report_rows.extend(existing_rows)
        processed_articles |= existing_processed

    article_list = []
    for _, row in df.iterrows():
        article = normalize_article(row.get(COL_ARTICLE, ""))
        if article and article not in processed_articles:
            article_list.append(article)

    with make_session() as session:
        sitemap_map = build_sitemap_map(article_list, session)
        total = len(df)

        for index, row in df.iterrows():
            article = normalize_article(row.get(COL_ARTICLE, ""))
            name = str(row.get(COL_NAME, "")).strip()
            if not article or article in processed_articles:
                continue

            print(f"[{index + 1}/{total}] {safe_console_text(article)} | {safe_console_text(name)}")

            try:
                product_url = sitemap_map.get(article)
                if not product_url:
                    raise ValueError("article_not_in_sitemap")
                product_url, image_urls, note = extract_product_data(article, product_url, session)
                if note != "ok":
                    raise ValueError(note)
                saved_ok, gallery_saved, save_note = save_product_images(article, image_urls, session)
                if not saved_ok:
                    raise ValueError(save_note)
                report_rows.append(
                    {
                        "article": article,
                        "name": name,
                        "source_name": SOURCE_NAME,
                        "product_url": product_url,
                        "status": "OK",
                        "images_found": len(image_urls),
                        "gallery_saved": gallery_saved,
                        "note": "ok",
                    }
                )
            except Exception as exc:
                report_rows.append(
                    {
                        "article": article,
                        "name": name,
                        "source_name": SOURCE_NAME,
                        "product_url": sitemap_map.get(article, ""),
                        "status": "FAIL",
                        "images_found": 0,
                        "gallery_saved": 0,
                        "note": str(exc).strip() or "unknown_error",
                    }
                )

            processed_articles.add(article)

            if len(report_rows) % SAVE_EVERY == 0:
                save_report(report_rows)

            time.sleep(SLEEP_BETWEEN_ITEMS)

    save_report(report_rows)
    ok_count = sum(1 for row in report_rows if row.get("status") == "OK")
    fail_count = sum(1 for row in report_rows if row.get("status") == "FAIL")
    print(f"Saved report: {REPORT_FILE}")
    print(f"OK: {ok_count}")
    print(f"FAIL: {fail_count}")


if __name__ == "__main__":
    main()
