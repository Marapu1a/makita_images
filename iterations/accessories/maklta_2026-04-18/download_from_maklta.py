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
REPORT_FILE = BASE_DIR / "output" / "maklta_report.xlsx"

BASE_URL = "https://maklta.com.ua"
SITEMAP_URL = BASE_URL + "/sitemap.xml"
SOURCE_NAME = "maklta.com.ua"

COL_ARTICLE = "Артикул [ARTIKUL]"
COL_NAME = "Наименование элемента"

REQUEST_TIMEOUT = 35
SLEEP_BETWEEN_ITEMS = 0.1
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


def normalize_slug_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


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


def load_sitemap_candidates(session: requests.Session) -> list[str]:
    text = fetch_text(SITEMAP_URL, session)
    return re.findall(r"<loc>(.*?)</loc>", text)


def find_product_candidates(article: str, locs: list[str]) -> list[str]:
    article_norm = normalize_article(article)
    slug_token = normalize_slug_token(article_norm.replace("/1", "").replace("/", "-"))
    candidates: list[str] = []
    for loc in locs:
        low = loc.lower()
        if slug_token in normalize_slug_token(low) or article_norm.lower() in low:
            candidates.append(loc)
    return candidates


def extract_product_images(product_url: str, article: str, session: requests.Session) -> tuple[str, list[str], str]:
    text = fetch_text(product_url, session)
    article_norm = normalize_article(article)
    article_token = normalize_slug_token(article_norm.replace("/1", "").replace("/", "-"))

    soup = BeautifulSoup(text, "html.parser")
    title_node = soup.find("title")
    title = title_node.get_text(" ", strip=True) if title_node else ""

    page_blob = normalize_slug_token(text)
    if article_token not in page_blob and normalize_slug_token(article_norm) not in page_blob:
        return title, [], "article_not_in_page"

    image_urls: list[str] = []
    for match in re.findall(r"/(?:image|userfiles/image)/catalog/[^\"'>\s]+\.(?:jpg|jpeg|png|webp)", text, flags=re.I):
        full = BASE_URL + match if match.startswith("/") else match
        if full not in image_urls:
            image_urls.append(full)

    filtered: list[str] = []
    for image_url in image_urls:
        low = image_url.lower()
        if "placeholder" in low or "no_image" in low or "no-image" in low:
            continue
        if article_token not in normalize_slug_token(low):
            continue
        filtered.append(image_url)

    if not filtered:
        return title, [], "no_images"

    return title, filtered[:1], "ok"


def choose_best_product(article: str, candidates: list[str], session: requests.Session) -> tuple[str | None, list[str], str]:
    for product_url in candidates:
        try:
            _, image_urls, note = extract_product_images(product_url, article, session)
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
    locs = load_sitemap_candidates(session)

    total = len(df)
    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        article = normalize_article(row.get(COL_ARTICLE, ""))
        name = str(row.get(COL_NAME, "")).strip()
        if not article or article in processed:
            continue

        console_name = safe_console_text(name)
        print(f"[{idx}/{total}] {article} | {console_name}")

        try:
            candidates = find_product_candidates(article, locs)
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
                        "note": save_note,
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
