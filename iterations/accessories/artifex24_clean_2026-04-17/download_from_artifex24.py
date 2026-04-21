from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path
import re
import time
from urllib.parse import urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "input" / "pictures.xlsx"
OUTPUT_DIR = BASE_DIR / "output" / "import_images"
REPORT_FILE = BASE_DIR / "output" / "artifex24_report.xlsx"

BASE_URL = "https://www.artifex24.de"
SEARCH_URL = BASE_URL + "/?qs={article}&search="
SOURCE_NAME = "artifex24.de"

COL_ARTICLE = "Артикул [ARTIKUL]"
COL_NAME = "Наименование элемента"

REQUEST_TIMEOUT = 40
FETCH_RETRIES = 2
DOWNLOAD_RETRIES = 2
RETRY_SLEEP = 0.5
SLEEP_BETWEEN_ITEMS = 0.08
SAVE_EVERY = 25
MIN_BYTES = 1000
MAX_GALLERY = 5

WEBP_QUALITY = 82
WEBP_METHOD = 6
MAX_WIDTH = 1600
MAX_HEIGHT = 1600
DUPLICATE_HASH_ALERT = 50

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


def fetch_response(url: str, session: requests.Session) -> requests.Response:
    last_error = None
    for _ in range(FETCH_RETRIES + 1):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            response.raise_for_status()
            return response
        except Exception as exc:
            last_error = exc
            time.sleep(RETRY_SLEEP)
    raise last_error


def is_probable_product_url(url: str, article: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path or ""
    query = parsed.query or ""
    article_token = normalize_token(article)
    if not path or path == "/":
        return False
    if query:
        return False
    if article_token not in normalize_token(path):
        return False
    return True


def extract_exact_result_url(article: str, html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    article_token = normalize_token(article)
    candidates: list[str] = []

    for node in soup.select("a[href]"):
        href = (node.get("href") or "").strip()
        if not href.startswith("http"):
            continue
        if "artifex24.de" not in href.lower():
            continue
        if not is_probable_product_url(href, article):
            continue
        text_blob = " ".join(
            [
                href,
                " ".join(node.get_text(" ", strip=True).split()),
                str(node.get("title") or ""),
            ]
        )
        if article_token in normalize_token(text_blob):
            candidates.append(href)

    if not candidates:
        return None
    unique_candidates = []
    for candidate in candidates:
        if candidate not in unique_candidates:
            unique_candidates.append(candidate)
    return unique_candidates[0]


def search_product(article: str, session: requests.Session) -> tuple[str | None, str]:
    response = fetch_response(SEARCH_URL.format(article=article), session)
    final_url = response.url.strip()
    final_text = response.text
    article_token = normalize_token(article)

    if not is_probable_product_url(final_url, article):
        result_url = extract_exact_result_url(article, final_text)
        if not result_url:
            return None, "article_not_in_final_url"
        result_response = fetch_response(result_url, session)
        final_url = result_response.url.strip()
        final_text = result_response.text
        if not is_probable_product_url(final_url, article):
            return None, "article_not_in_final_url"
    if article_token not in normalize_token(final_text):
        return None, "article_not_in_page"

    return final_url, "ok"


def canonicalize_image_url(url: str) -> str:
    return url.split("?")[0]


def image_variant_key(url: str) -> str:
    url = canonicalize_image_url(url)
    return re.sub(r"/(xs|sm|md|lg)/", "/size/", url, flags=re.I)


def image_priority(url: str) -> tuple[int, int]:
    lowered = url.lower()
    size_score = 0
    if "/lg/" in lowered:
        size_score = 4
    elif "/md/" in lowered:
        size_score = 3
    elif "/sm/" in lowered:
        size_score = 2
    elif "/xs/" in lowered:
        size_score = 1
    variant_penalty = -1 if "~2" in lowered or "~3" in lowered or "~4" in lowered else 0
    return size_score, variant_penalty


def image_matches_article(article_token: str, image_url: str, node_text: str = "") -> bool:
    if article_token in normalize_token(image_url):
        return True
    if node_text and article_token in normalize_token(node_text):
        return True
    return False


def collect_existing_hash_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    if not OUTPUT_DIR.exists():
        return counts
    for folder in OUTPUT_DIR.iterdir():
        preview = folder / "preview.webp"
        if not folder.is_dir() or not preview.exists():
            continue
        file_hash = hashlib.md5(preview.read_bytes()).hexdigest()
        counts[file_hash] = counts.get(file_hash, 0) + 1
    return counts


def extract_product_data(article: str, product_url: str, session: requests.Session) -> tuple[str, list[str], str]:
    response = fetch_response(product_url, session)
    text = response.text
    article_token = normalize_token(article)
    if article_token not in normalize_token(text):
        return "", [], "article_not_in_page"

    soup = BeautifulSoup(text, "html.parser")
    image_map: dict[str, str] = {}

    for node in soup.select("meta[property='og:image'], img[src], img[data-src], img[data-full-image]"):
        src = node.get("content") or node.get("data-full-image") or node.get("data-src") or node.get("src") or ""
        if not src:
            continue
        full_url = src.strip()
        if full_url.startswith("/"):
            full_url = BASE_URL + full_url
        if "/media/image/product/" not in full_url.lower():
            continue
        node_text = " ".join(
            [
                str(node.get("alt") or ""),
                str(node.get("title") or ""),
                str(node.get("data-caption") or ""),
            ]
        )
        if not image_matches_article(article_token, full_url, node_text):
            continue
        full_url = canonicalize_image_url(full_url)
        variant_key = image_variant_key(full_url)
        current = image_map.get(variant_key)
        if current is None or image_priority(full_url) > image_priority(current):
            image_map[variant_key] = full_url

    image_urls = sorted(image_map.values(), key=image_priority, reverse=True)
    if not image_urls:
        return "", [], "no_matching_images"

    return product_url, image_urls[: 1 + MAX_GALLERY], "ok"


def prepare_image_for_webp(image: Image.Image) -> Image.Image:
    has_alpha = image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)
    image = image.convert("RGBA" if has_alpha else "RGB")
    image.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.LANCZOS)
    return image


def download_and_compress_image(
    url: str,
    target_path: Path,
    session: requests.Session,
    existing_hash_counts: dict[str, int],
) -> tuple[bool, str]:
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
            temp_buffer = BytesIO()
            image.save(temp_buffer, format="WEBP", quality=WEBP_QUALITY, method=WEBP_METHOD)
            image_bytes = temp_buffer.getvalue()
            file_hash = hashlib.md5(image_bytes).hexdigest()
            if existing_hash_counts.get(file_hash, 0) >= DUPLICATE_HASH_ALERT:
                last_reason = "suspicious_duplicate_hash"
                raise ValueError(last_reason)
            target_path.write_bytes(image_bytes)
            existing_hash_counts[file_hash] = existing_hash_counts.get(file_hash, 0) + 1
            return True, "ok"
        except Exception as exc:
            if str(exc).strip():
                last_reason = str(exc).strip()
            time.sleep(RETRY_SLEEP)
    return False, last_reason


def save_product_images(
    article: str,
    image_urls: list[str],
    session: requests.Session,
    existing_hash_counts: dict[str, int],
) -> tuple[bool, int, str]:
    if not image_urls:
        return False, 0, "no_images"

    item_dir = OUTPUT_DIR / safe_name(article)
    item_dir.mkdir(parents=True, exist_ok=True)

    preview_ok, note = download_and_compress_image(image_urls[0], item_dir / "preview.webp", session, existing_hash_counts)
    if not preview_ok:
        return False, 0, f"preview_failed:{note}"

    gallery_saved = 0
    for image_url in image_urls[1:]:
        gallery_path = item_dir / f"gallery_{gallery_saved + 1:02}.webp"
        ok, _ = download_and_compress_image(image_url, gallery_path, session, existing_hash_counts)
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

    with make_session() as session:
        existing_hash_counts = collect_existing_hash_counts()
        total = len(df)
        for index, row in df.iterrows():
            article = str(row.get(COL_ARTICLE, "")).strip()
            name = str(row.get(COL_NAME, "")).strip()
            article_norm = normalize_article(article)

            if article_norm in processed_articles:
                continue

            print(f"[{index + 1}/{total}] {safe_console_text(article)} | {safe_console_text(name)}")

            try:
                product_url, note = search_product(article_norm, session)
                if not product_url:
                    raise ValueError(note)
                product_url, image_urls, note = extract_product_data(article_norm, product_url, session)
                if note != "ok":
                    raise ValueError(note)
                saved_ok, gallery_saved, save_note = save_product_images(article_norm, image_urls, session, existing_hash_counts)
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
