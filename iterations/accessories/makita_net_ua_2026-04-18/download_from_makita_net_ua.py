from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.parse import quote_plus, urlsplit, urlunsplit
import re
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "input" / "pictures.xlsx"
OUTPUT_DIR = BASE_DIR / "output" / "import_images"
REPORT_FILE = BASE_DIR / "output" / "makita_net_ua_report.xlsx"

BASE_URL = "https://makita.net.ua"
SEARCH_URL = BASE_URL + "/ru/search?search_query={query}"
SOURCE_NAME = "makita.net.ua"

COL_ARTICLE = "Артикул [ARTIKUL]"
COL_NAME = "Наименование элемента"

REQUEST_TIMEOUT = 35
SLEEP_BETWEEN_ITEMS = 0.12
FETCH_RETRIES = 2
DOWNLOAD_RETRIES = 2
RETRY_SLEEP = 0.5
SAVE_EVERY = 25
MIN_BYTES = 1000

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


def strip_query(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


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
    text = fetch_text(SEARCH_URL.format(query=quote_plus(article)), session)
    soup = BeautifulSoup(text, "html.parser")

    article_norm = normalize_article(article)
    article_token = normalize_token(article_norm)
    results: list[str] = []
    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        if not ("/ru/" in href or "/uk/" in href):
            continue
        full_url = href if href.startswith("http") else BASE_URL + href
        full_url = strip_query(full_url)
        blob = normalize_token(f"{full_url} {' '.join(link.stripped_strings)}")
        if article_token not in blob:
            continue
        if full_url.startswith(SEARCH_URL.split("{query}")[0]):
            continue
        if "/search" in full_url:
            continue
        if full_url not in results:
            results.append(full_url)
    return results


def image_sort_key(url: str) -> tuple[int, int, str]:
    lower = url.lower()
    if "ws-store_large" in lower:
        return (0, 0, lower)
    if "ws-store_thickbox" in lower:
        return (1, 0, lower)
    return (2, 0, lower)


def extract_product_images(product_url: str, article: str, session: requests.Session) -> tuple[str, list[str], str]:
    text = fetch_text(product_url, session)
    soup = BeautifulSoup(text, "html.parser")
    article_norm = normalize_article(article)
    article_token = normalize_token(article_norm)

    body_token = normalize_token(text)
    if article_token not in body_token:
        return "", [], "article_not_in_page"

    title_node = soup.find("title")
    title = title_node.get_text(" ", strip=True) if title_node else ""

    image_urls: list[str] = []

    og_image = soup.find("meta", attrs={"property": "og:image"})
    if og_image and og_image.get("content"):
        image_urls.append(strip_query(og_image["content"].strip()))

    for match in re.findall(r"/\d+-ws-store_(?:large|thickbox)/[^\"'>\s]+", text, flags=re.I):
        image_urls.append(strip_query(BASE_URL + match))

    unique_urls: list[str] = []
    for image_url in image_urls:
        lower = image_url.lower()
        if "data:image/" in lower:
            continue
        if "default" in lower or "placeholder" in lower or "no-image" in lower or "noimage" in lower:
            continue
        if "ws-store_large" not in lower and "ws-store_thickbox" not in lower:
            continue
        image_blob = normalize_token(image_url)
        if article_token not in image_blob and image_url not in unique_urls[:1]:
            continue
        if image_url not in unique_urls:
            unique_urls.append(image_url)

    unique_urls.sort(key=image_sort_key)
    if not unique_urls:
        return title, [], "no_images"

    # Conservative mode: trust the main card image first. Additional images are rare here and
    # keeping the run strict helps avoid pulling unrelated gallery noise from recommendation blocks.
    return title, unique_urls[:1], "ok"


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
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_excel(REPORT_FILE, index=False)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(INPUT_FILE)
    report_rows, processed = load_existing_report()
    resumed_rows, resumed_processed = build_existing_folder_rows(df)
    if resumed_rows and not report_rows:
        report_rows = resumed_rows
        processed = resumed_processed

    session = make_session()

    total = len(df)
    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        article = normalize_article(row.get(COL_ARTICLE, ""))
        name = str(row.get(COL_NAME, "")).strip()
        if not article:
            continue
        if article in processed:
            continue

        console_name = safe_console_text(name)
        print(f"[{idx}/{total}] {article} | {console_name}")

        try:
            candidates = search_products(article, session)
            product_url, image_urls, note = choose_best_product(article, candidates, session)
            if note != "ok" or not product_url or not image_urls:
                report_rows.append(
                    {
                        "article": article,
                        "name": name,
                        "source_name": SOURCE_NAME,
                        "product_url": product_url or "",
                        "status": "FAIL",
                        "images_found": len(image_urls),
                        "gallery_saved": 0,
                        "note": note,
                    }
                )
                processed.add(article)
            else:
                ok, gallery_saved, save_note = save_product_images(article, image_urls, session)
                report_rows.append(
                    {
                        "article": article,
                        "name": name,
                        "source_name": SOURCE_NAME,
                        "product_url": product_url,
                        "status": "OK" if ok else "FAIL",
                        "images_found": len(image_urls),
                        "gallery_saved": gallery_saved,
                        "note": save_note if ok else save_note,
                    }
                )
                processed.add(article)
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
                    "note": f"error:{type(exc).__name__}",
                }
            )
            processed.add(article)

        if len(report_rows) % SAVE_EVERY == 0:
            save_report(report_rows)
        time.sleep(SLEEP_BETWEEN_ITEMS)

    save_report(report_rows)

    ok_count = sum(1 for row in report_rows if row.get("status") == "OK")
    print(f"Done. OK={ok_count}, total_report_rows={len(report_rows)}")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
