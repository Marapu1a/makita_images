from __future__ import annotations

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
REPORT_FILE = BASE_DIR / "output" / "makita_russia_shop_report.xlsx"

BASE_URL = "https://makita-russia.shop"
SITEMAP_URL = BASE_URL + "/sitemap"
SOURCE_NAME = "makita-russia.shop"

COL_ARTICLE = "Артикул [ARTIKUL]"
COL_NAME = "Наименование элемента"

REQUEST_TIMEOUT = 35
FETCH_RETRIES = 2
DOWNLOAD_RETRIES = 2
RETRY_SLEEP = 0.5
SLEEP_BETWEEN_ITEMS = 0.06
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


def fetch_text(url: str, session: requests.Session) -> str:
    return fetch_response(url, session).text


def score_candidate(article: str, href: str, text: str) -> int:
    article_token = normalize_token(article)
    href_token = normalize_token(href)
    text_token = normalize_token(text)
    score = 0

    if article_token in href_token:
        score += 3
    if article_token in text_token:
        score += 3
    if href_token.endswith(article_token):
        score += 7
    if text_token.endswith(article_token):
        score += 6

    slug = urlparse(href).path.rstrip("/").split("/")[-1]
    if normalize_token(slug).endswith(article_token):
        score += 8

    extra_articles = re.findall(r"[A-Z0-9]{1,6}-[A-Z0-9-]{1,10}", f"{href} {text}".upper())
    other_articles = {item for item in extra_articles if normalize_token(item) != article_token}
    score -= len(other_articles) * 2

    return score


def build_sitemap_map(articles: list[str], session: requests.Session) -> dict[str, str]:
    html = fetch_text(SITEMAP_URL, session)
    soup = BeautifulSoup(html, "html.parser")
    wanted = {article: normalize_token(article) for article in articles}
    candidates: dict[str, list[tuple[int, str]]] = {article: [] for article in articles}

    for anchor in soup.select("a[href]"):
        href = (anchor.get("href") or "").strip()
        if not href.startswith(BASE_URL):
            continue
        text = " ".join(anchor.stripped_strings)
        combined_token = normalize_token(f"{href} {text}")
        for article, article_token in wanted.items():
            if article_token and article_token in combined_token:
                score = score_candidate(article, href, text)
                if score > 0:
                    candidates[article].append((score, href))

    resolved: dict[str, str] = {}
    for article, rows in candidates.items():
        if not rows:
            continue
        rows.sort(key=lambda item: (-item[0], len(item[1]), item[1]))
        resolved[article] = rows[0][1]
    return resolved


def canonicalize_image_url(url: str) -> str:
    return url.split("?")[0]


def is_real_product_image(url: str) -> bool:
    lowered = url.lower()
    if "/media/catalog/product/" not in lowered:
        return False
    if "/media/catalog/category/" in lowered:
        return False
    if "placeholder" in lowered or "logo" in lowered or "watermark" in lowered:
        return False
    return True


def image_priority(url: str) -> tuple[int, int, str]:
    lowered = url.lower()
    score = 0
    if "/image/" in lowered:
        score += 4
    if "/small_image/" in lowered:
        score -= 2
    if lowered.endswith(".jpg") or lowered.endswith(".jpeg"):
        score += 2
    if lowered.endswith(".webp"):
        score -= 1
    return (-score, len(url), url)


def extract_product_data(article: str, product_url: str, session: requests.Session) -> tuple[str, list[str], str]:
    text = fetch_text(product_url, session)
    if normalize_token(article) not in normalize_token(text):
        return product_url, [], "article_not_in_page"

    soup = BeautifulSoup(text, "html.parser")
    image_urls: list[str] = []

    for node in soup.select("meta[property='og:image'], img[src], img[data-src], source[srcset]"):
        raw = node.get("content") or node.get("data-src") or node.get("src") or node.get("srcset") or ""
        if not raw:
            continue
        for chunk in str(raw).split(","):
            part = chunk.strip().split(" ")[0]
            if not part:
                continue
            if part.startswith("/"):
                part = BASE_URL + part
            if not part.startswith("http"):
                continue
            if not is_real_product_image(part):
                continue
            canonical = canonicalize_image_url(part)
            if canonical not in image_urls:
                image_urls.append(canonical)

    image_urls.sort(key=image_priority)

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
