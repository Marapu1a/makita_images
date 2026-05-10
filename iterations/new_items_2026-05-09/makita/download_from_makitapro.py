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
REPORT_FILE = BASE_DIR / "output" / "makitapro_report.xlsx"

BASE_URL = "https://www.makitapro.ru"
SEARCH_URL = BASE_URL + "/search/index.html?order=tools&term={query}"
SOURCE_NAME = "makitapro.ru"

COL_ARTICLE = "Артикул [ARTIKUL]"
COL_NAME = "Наименование элемента"

REQUEST_TIMEOUT = 40
SLEEP_BETWEEN_ITEMS = 0.12
MAX_GALLERY = 6
MIN_BYTES = 1000
DOWNLOAD_RETRIES = 2
RETRY_SLEEP = 0.5
FETCH_RETRIES = 2
SAVE_EVERY = 25

WEBP_QUALITY = 82
WEBP_METHOD = 6
MAX_WIDTH = 1600
MAX_HEIGHT = 1600

Image.MAX_IMAGE_PIXELS = None


def normalize_article(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().upper()
    return re.sub(r"\s+", "", text)


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


def search_products(article: str, session: requests.Session) -> list[str]:
    url = SEARCH_URL.format(query=quote_plus(article))
    text = fetch_text(url, session)
    soup = BeautifulSoup(text, "html.parser")

    article_token = normalize_token(article)
    results: list[str] = []
    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        if not re.search(r"-i\d+\.html$", href):
            continue
        full_url = urljoin(BASE_URL, href)
        blob = normalize_token(f"{href} {' '.join(link.stripped_strings)}")
        if article_token not in blob:
            continue
        if full_url not in results:
            results.append(full_url)
    return results


def image_sort_key(url: str) -> tuple[int, int, int, str]:
    lower = url.lower()
    large_score = 0 if "large" in lower else 1
    item_score = 0 if "/u/catalog_item_images/" in lower else 1
    thumb_penalty = 1 if "thumbnail" in lower or "x300" in lower or "-300" in lower else 0
    return (large_score, item_score, thumb_penalty, lower)


def extract_product_images(product_url: str, article: str, session: requests.Session) -> tuple[str, list[str], str]:
    text = fetch_text(product_url, session)
    soup = BeautifulSoup(text, "html.parser")
    article_norm = normalize_article(article)
    if article_norm not in normalize_article(text):
        return "", [], "article_not_in_page"

    title_node = soup.find("title")
    title = title_node.get_text(" ", strip=True) if title_node else ""

    id_match = re.search(r"-i(\d+)\.html$", product_url)
    product_id = id_match.group(1) if id_match else ""

    image_urls: list[str] = []
    for node in soup.select("img[src], img[data-src], a[href]"):
        value = node.get("data-src") or node.get("src") or node.get("href") or ""
        if not value:
            continue
        if value.startswith("/"):
            value = urljoin(BASE_URL, value)
        lower = value.lower()
        if not lower.startswith(BASE_URL.lower()):
            continue
        if "/u/catalog/" not in lower and "/u/catalog_item_images/" not in lower:
            continue
        if "thumbnail" in lower or "/item/icon.html" in lower:
            continue
        if product_id and f"/{product_id}" not in lower and f"{product_id}-" not in lower:
            continue
        if value not in image_urls:
            image_urls.append(value)

    image_urls.sort(key=image_sort_key)
    if not image_urls:
        return title, [], "no_images"

    return title, image_urls[:MAX_GALLERY], "ok"


def choose_best_product(article: str, candidates: list[str], session: requests.Session) -> tuple[str | None, list[str], str]:
    article_norm = normalize_article(article)
    for product_url in candidates:
        try:
            _, image_urls, note = extract_product_images(product_url, article_norm, session)
        except Exception:
            continue
        if note == "ok" and image_urls:
            return product_url, image_urls, "ok"
    if candidates:
        return candidates[0], [], "no_images"
    return None, [], "not_found"


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

    gallery_saved = 0
    for idx, image_url in enumerate(image_urls[1:], start=1):
        ok, gallery_note = download_and_compress_image(image_url, item_dir / f"gallery_{idx:02d}.webp", session)
        if not ok:
            continue
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


def save_report(rows: list[dict]) -> None:
    pd.DataFrame(rows).to_excel(REPORT_FILE, index=False)


def main() -> None:
    df = pd.read_excel(INPUT_FILE)
    report_rows, processed_articles = load_existing_report()
    if not report_rows:
        existing_rows, existing_processed = build_existing_folder_rows(df)
        report_rows.extend(existing_rows)
        processed_articles |= existing_processed

    with make_session() as session:
        total = len(df)
        for index, row in df.iterrows():
            article = normalize_article(row.get(COL_ARTICLE, ""))
            name = str(row.get(COL_NAME, "")).strip()
            if not article or article in processed_articles:
                continue

            print(f"[{index + 1}/{total}] {safe_console_text(article)} | {safe_console_text(name)}")

            try:
                candidates = search_products(article, session)
                product_url, image_urls, note = choose_best_product(article, candidates, session)
                if note != "ok" or not product_url:
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
                        "product_url": "",
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
