from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin
import re
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup
from PIL import Image
import urllib3


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "input" / "pictures.xlsx"
OUTPUT_DIR = BASE_DIR / "output" / "import_images"
REPORT_FILE = BASE_DIR / "output" / "makitatools_report.xlsx"

BASE_URL = "https://makitatools.com"
DETAIL_URL = BASE_URL + "/products/details/{article}"
SOURCE_NAME = "makitatools.com"

COL_ARTICLE = "Артикул [ARTIKUL]"
COL_NAME = "Наименование элемента"

REQUEST_TIMEOUT = 40
FETCH_RETRIES = 2
DOWNLOAD_RETRIES = 2
RETRY_SLEEP = 0.5
SLEEP_BETWEEN_ITEMS = 0.15
MAX_GALLERY = 5
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
            response = session.get(url, timeout=REQUEST_TIMEOUT, verify=False)
            response.raise_for_status()
            return response.text
        except Exception as exc:
            last_error = exc
            time.sleep(RETRY_SLEEP)
    raise last_error


def canonical_image_key(url: str) -> str:
    filename = url.split("/")[-1].split("?")[0]
    filename = re.sub(r"_(500|1500)px(?=\.)", "", filename, flags=re.I)
    return filename.lower()


def image_rank(url: str) -> tuple[int, int, str]:
    filename = url.split("/")[-1].split("?")[0].lower()
    size_rank = 0
    if "_1500px" in filename:
        size_rank = 2
    elif "_500px" in filename:
        size_rank = 1

    variant_rank = 9
    for idx, token in enumerate(["_p_", "_a_", "_g_", "_f_", "_fc_"]):
        if token in filename:
            variant_rank = idx
            break

    return (variant_rank, -size_rank, filename)


def extract_product_data(article: str, session: requests.Session) -> tuple[str | None, str, list[str], str]:
    product_url = DETAIL_URL.format(article=article)
    text = fetch_text(product_url, session)

    final_url = product_url
    if "/products/details/" not in product_url:
        return None, "", [], "invalid_detail_url"

    soup = BeautifulSoup(text, "html.parser")

    model_node = soup.select_one(".model-number")
    found_article = " ".join(model_node.get_text(" ", strip=True).split()) if model_node else ""

    if normalize_article(found_article) != normalize_article(article):
        return None, found_article, [], "article_mismatch"

    image_urls = re.findall(r'https://[^"\']+\.(?:jpg|jpeg|png|webp)', text, flags=re.I)
    cms_images = [url for url in image_urls if "/apps/cms/img/" in url.lower()]

    article_token = normalize_token(article)
    filtered: list[str] = []
    seen_keys: dict[str, str] = {}

    for image_url in cms_images:
        filename = image_url.split("/")[-1].split("?")[0]
        if article_token not in normalize_token(filename):
            continue

        key = canonical_image_key(image_url)
        current = seen_keys.get(key)
        if current is None or image_rank(image_url) < image_rank(current):
            seen_keys[key] = image_url

    filtered = sorted(seen_keys.values(), key=image_rank)

    if not filtered:
        return product_url, found_article, [], "no_matching_images"

    return product_url, found_article, filtered, "ok"


def prepare_image_for_webp(image: Image.Image) -> Image.Image:
    has_alpha = image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)
    image = image.convert("RGBA" if has_alpha else "RGB")
    image.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.LANCZOS)
    return image


def download_and_compress_image(url: str, target_path: Path, session: requests.Session) -> tuple[bool, str]:
    last_reason = "unknown"

    for _ in range(DOWNLOAD_RETRIES + 1):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT, verify=False)
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

    preview_ok, preview_reason = download_and_compress_image(
        image_urls[0], item_dir / "preview.webp", session
    )
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

        gallery_saved = len(list(folder.glob("gallery_*.webp")))
        rows.append(
            {
                "article": article,
                "name": names.get(article, ""),
                "source_name": SOURCE_NAME,
                "product_url": "",
                "found_article": article,
                "status": "OK",
                "images_found": gallery_saved + 1,
                "gallery_saved": gallery_saved,
                "note": "existing_folder_resumed",
            }
        )
        processed.add(article)

    return rows, processed


def merge_missing_existing_folders(
    report_rows: list[dict], processed_articles: set[str], df: pd.DataFrame
) -> tuple[list[dict], set[str], int]:
    existing_rows, existing_processed = build_existing_folder_rows(df)
    added = 0

    for row in existing_rows:
        article = normalize_article(row.get("article"))
        if article in processed_articles:
            continue
        report_rows.append(row)
        processed_articles.add(article)
        added += 1

    return report_rows, processed_articles, added


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
    else:
        report_rows, processed_articles, added_rows = merge_missing_existing_folders(
            report_rows, processed_articles, df
        )
        if added_rows:
            pd.DataFrame(report_rows).to_excel(REPORT_FILE, index=False)

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
                        "product_url": "",
                        "found_article": "",
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

            try:
                product_url, found_article, image_urls, note = extract_product_data(article, session)
            except Exception as exc:
                fail_count += 1
                report_rows.append(
                    {
                        "article": article,
                        "name": name,
                        "source_name": SOURCE_NAME,
                        "product_url": "",
                        "found_article": "",
                        "status": "FAIL",
                        "images_found": 0,
                        "gallery_saved": 0,
                        "note": f"fetch_error:{exc}",
                    }
                )
                processed_articles.add(article_norm)
                if len(report_rows) % SAVE_EVERY == 0:
                    pd.DataFrame(report_rows).to_excel(REPORT_FILE, index=False)
                time.sleep(SLEEP_BETWEEN_ITEMS)
                continue

            if not product_url or not image_urls:
                fail_count += 1
                report_rows.append(
                    {
                        "article": article,
                        "name": name,
                        "source_name": SOURCE_NAME,
                        "product_url": product_url or "",
                        "found_article": found_article,
                        "status": "FAIL",
                        "images_found": len(image_urls),
                        "gallery_saved": 0,
                        "note": note,
                    }
                )
                processed_articles.add(article_norm)
                if len(report_rows) % SAVE_EVERY == 0:
                    pd.DataFrame(report_rows).to_excel(REPORT_FILE, index=False)
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
                    "product_url": product_url,
                    "found_article": found_article,
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

    print("\n=== MAKITATOOLS DOWNLOAD SUMMARY ===")
    print(f"Input rows: {len(df)}")
    print(f"OK: {ok_count}")
    print(f"FAIL: {fail_count}")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
