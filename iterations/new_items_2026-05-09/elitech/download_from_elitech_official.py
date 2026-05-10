from __future__ import annotations

import concurrent.futures as futures
import io
import re
import time
from collections import Counter
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
from bs4 import BeautifulSoup
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
INPUT_XLSX = BASE_DIR / "output" / "remaining_after_elitech_official.xlsx"
OUTPUT_DIR = BASE_DIR / "output"
IMPORT_DIR = OUTPUT_DIR / "import_images"
REPORT_XLSX = OUTPUT_DIR / "elitech_official_report.xlsx"
REMAINING_XLSX = OUTPUT_DIR / "remaining_after_elitech_official.xlsx"
SITEMAP_URL = "https://elitech.ru/sitemapiblock2.xml"
SITE_ROOT = "https://elitech.ru"
TIMEOUT = 30
MAX_WORKERS = 10


def norm_article(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().upper()
    text = re.sub(r"\s+", "", text)
    return text


def safe_folder_name(article: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", article.strip())


def detect_article_col(df: pd.DataFrame) -> str:
    for col in df.columns:
        if "ARTIKUL" in str(col).upper():
            return col
    raise RuntimeError("Article column not found")


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
            ),
            "Accept-Language": "ru,en;q=0.9",
        }
    )
    return session


def fetch_sitemap_product_urls(session: requests.Session) -> list[str]:
    resp = session.get(SITEMAP_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    urls = re.findall(r"<loc>(.*?)</loc>", resp.text)
    return [url for url in urls if "/catalog/product/" in url]


def extract_article(html: str) -> str:
    match = re.search(r"Артикул:\s*</?.*?>?\s*([A-Za-zА-Яа-я0-9\-_/\.]+)", html)
    if match:
        return norm_article(match.group(1))
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    match = re.search(r"Артикул:\s*([A-Za-zА-Яа-я0-9\-_/\.]+)", text)
    return norm_article(match.group(1)) if match else ""


def extract_images(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    images: list[str] = []

    for link in soup.select('link[itemprop="image"]'):
        href = (link.get("href") or "").strip()
        if href:
            images.append(requests.compat.urljoin(SITE_ROOT, href))

    for anchor in soup.select("div.product-slider__img-wrap a[href]"):
        href = (anchor.get("href") or "").strip()
        if href:
            images.append(requests.compat.urljoin(SITE_ROOT, href))

    unique: list[str] = []
    seen: set[str] = set()
    for image_url in images:
        clean = image_url.split("?")[0]
        if clean not in seen:
            seen.add(clean)
            unique.append(clean)
    return unique


def probe_product(url: str, targets: set[str]) -> tuple[str, dict] | None:
    session = make_session()
    try:
        resp = session.get(url, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        article = extract_article(resp.text)
        if not article or article not in targets:
            return None
        images = extract_images(resp.text)
        return article, {"product_url": url, "image_urls": images}
    except Exception:
        return None


def build_index(targets: set[str]) -> dict[str, dict]:
    session = make_session()
    urls = fetch_sitemap_product_urls(session)
    index: dict[str, dict] = {}

    with futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        future_map = {pool.submit(probe_product, url, targets): url for url in urls}
        for future in futures.as_completed(future_map):
            result = future.result()
            if not result:
                continue
            article, payload = result
            current = index.get(article)
            if current is None or len(payload["image_urls"]) > len(current["image_urls"]):
                index[article] = payload
    return index


def ensure_webp(image_bytes: bytes, destination: Path) -> bool:
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            destination.parent.mkdir(parents=True, exist_ok=True)
            img.save(destination, "WEBP", quality=90, method=6)
        return True
    except Exception:
        return False


def download_image(session: requests.Session, image_url: str, destination: Path) -> bool:
    try:
        resp = session.get(image_url, timeout=TIMEOUT)
        if resp.status_code != 200:
            return False
        content_type = (resp.headers.get("Content-Type") or "").lower()
        if "image" not in content_type:
            return False
        return ensure_webp(resp.content, destination)
    except Exception:
        return False


def build_remaining(df: pd.DataFrame, article_col: str) -> pd.DataFrame:
    confirmed = set()
    if IMPORT_DIR.exists():
        for folder in IMPORT_DIR.iterdir():
            if not folder.is_dir():
                continue
            if (folder / "preview.webp").exists():
                confirmed.add(norm_article(folder.name))
    article_series = df[article_col].astype(str).map(norm_article)
    return df.loc[~article_series.isin(confirmed)].copy()


def main() -> None:
    started = time.time()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(INPUT_XLSX)
    article_col = detect_article_col(df)
    df["_article_norm"] = df[article_col].map(norm_article)
    targets = {value for value in df["_article_norm"].tolist() if value}

    print(f"Input rows: {len(df)}")
    print(f"Unique target articles: {len(targets)}")
    print("Building official product index from sitemap...")
    index = build_index(targets)
    print(f"Indexed matched articles: {len(index)}")

    session = make_session()
    report_rows: list[dict] = []
    status_counter: Counter[str] = Counter()

    for row in df.to_dict("records"):
        article = row[article_col]
        article_norm = row["_article_norm"]
        folder = IMPORT_DIR / safe_folder_name(str(article))
        entry = index.get(article_norm)

        status = "FAIL"
        reason = "not_found"
        product_url = ""
        image_count = 0

        if entry:
            product_url = entry["product_url"]
            image_urls = entry["image_urls"]
            saved_files: list[Path] = []

            for idx, image_url in enumerate(image_urls):
                filename = "preview.webp" if idx == 0 else f"gallery_{idx:02d}.webp"
                destination = folder / filename
                if download_image(session, image_url, destination):
                    saved_files.append(destination)

            if saved_files:
                status = "OK"
                reason = ""
                image_count = len(saved_files)
            else:
                reason = "no_images"

        status_counter[status] += 1
        report_rows.append(
            {
                article_col: article,
                "name": row.get("Наименование элемента", ""),
                "section": row.get("Название основного раздела", ""),
                "status": status,
                "reason": reason,
                "product_url": product_url,
                "image_count": image_count,
                "folder_name": safe_folder_name(str(article)),
                "source": "elitech.ru",
            }
        )

    report_df = pd.DataFrame(report_rows)
    report_df.to_excel(REPORT_XLSX, index=False)

    remaining_df = build_remaining(df.drop(columns=["_article_norm"]), article_col)
    remaining_df.to_excel(REMAINING_XLSX, index=False)

    print("Done.")
    print(f"OK: {status_counter['OK']}")
    print(f"FAIL: {status_counter['FAIL']}")
    print(f"Remaining: {len(remaining_df)}")
    print(f"Elapsed seconds: {int(time.time() - started)}")


if __name__ == "__main__":
    main()
