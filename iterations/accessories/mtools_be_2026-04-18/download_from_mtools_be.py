from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import time

import pandas as pd
import requests
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "input" / "pictures.xlsx"
OUTPUT_DIR = BASE_DIR / "output" / "import_images"
REPORT_FILE = BASE_DIR / "output" / "mtools_be_report.xlsx"

SOURCE_NAME = "mtools.be"
SITEMAP_INDEX_URL = "https://www.mtools.be/sitemap/sitemap_be.xml"

COL_ARTICLE = "Артикул [ARTIKUL]"
COL_NAME = "Наименование элемента"

REQUEST_TIMEOUT = 45
FETCH_RETRIES = 2
DOWNLOAD_RETRIES = 2
RETRY_SLEEP = 0.5
SAVE_EVERY = 25
MIN_BYTES = 1500

WEBP_QUALITY = 82
WEBP_METHOD = 6
MAX_WIDTH = 1600
MAX_HEIGHT = 1600

Image.MAX_IMAGE_PIXELS = None


def normalize_article(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().upper()


def slug_token(article: str) -> str:
    return normalize_article(article).lower().replace("/", "-")


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


def load_sitemap_text(session: requests.Session) -> str:
    index_text = fetch_text(SITEMAP_INDEX_URL, session)
    sitemap_urls = re.findall(r"<loc>(.*?)</loc>", index_text)
    chunks: list[str] = []
    for sitemap_url in sitemap_urls:
        if "sitemap_be_" not in sitemap_url:
            continue
        chunks.append(fetch_text(sitemap_url, session))
    return "".join(chunks).lower()


def find_product(article: str, sitemap_text: str) -> tuple[str | None, str | None, str]:
    token = slug_token(article)
    pattern = (
        r"<url><loc>([^<]*"
        + re.escape(token)
        + r"[^<]*)</loc>.*?<image:loc>([^<]+)</image:loc>"
    )
    match = re.search(pattern, sitemap_text, re.S)
    if not match:
        return None, None, "not_found"

    product_url = match.group(1)
    image_url = match.group(2)
    image_name = image_url.rsplit("/", 1)[-1].lower()

    # Only trust media files whose own filename contains the article token.
    if token not in image_name:
        return product_url, None, "unsafe_image_name"

    return product_url, image_url, "ok"


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


def save_product_images(article: str, image_url: str, session: requests.Session) -> tuple[bool, str]:
    item_dir = OUTPUT_DIR / safe_name(article)
    item_dir.mkdir(parents=True, exist_ok=True)
    ok, note = download_and_compress_image(image_url, item_dir / "preview.webp", session)
    if not ok:
        return False, f"preview_failed:{note}"
    return True, "ok"


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
        processed.add(article)
        rows.append(
            {
                "source": SOURCE_NAME,
                "article": article,
                "name": names.get(article, ""),
                "status": "OK",
                "note": "existing_folder",
                "product_url": "",
                "image_url": "",
            }
        )
    return rows, processed


def save_report(rows: list[dict]) -> None:
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_excel(REPORT_FILE, index=False)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(INPUT_FILE)
    df[COL_ARTICLE] = df[COL_ARTICLE].map(normalize_article)
    df = df[df[COL_ARTICLE].astype(bool)].copy()
    df.reset_index(drop=True, inplace=True)

    session = make_session()
    sitemap_text = load_sitemap_text(session)

    report_rows, processed = load_existing_report()
    existing_rows, existing_processed = build_existing_folder_rows(df)
    if existing_rows:
        seen = {normalize_article(row.get("article")) for row in report_rows}
        for row in existing_rows:
            if row["article"] not in seen:
                report_rows.append(row)
        processed |= existing_processed
        save_report(report_rows)

    total = len(df)
    done = 0

    for _, row in df.iterrows():
        article = normalize_article(row.get(COL_ARTICLE, ""))
        name = str(row.get(COL_NAME, "")).strip()
        if not article or article in processed:
            continue

        product_url = ""
        image_url = ""
        status = "FAIL"
        note = ""

        try:
            product_url, image_url, note = find_product(article, sitemap_text)
            if note == "ok" and product_url and image_url:
                saved, save_note = save_product_images(article, image_url, session)
                if saved:
                    status = "OK"
                    note = "ok"
                else:
                    note = save_note
            else:
                status = "FAIL"
        except Exception as exc:
            note = f"error:{type(exc).__name__}"

        report_rows.append(
            {
                "source": SOURCE_NAME,
                "article": article,
                "name": name,
                "status": status,
                "note": note,
                "product_url": product_url or "",
                "image_url": image_url or "",
            }
        )
        processed.add(article)
        done += 1

        if done % SAVE_EVERY == 0:
            save_report(report_rows)

    save_report(report_rows)
    print(f"{SOURCE_NAME}: processed={done} total_input={total}")


if __name__ == "__main__":
    main()
