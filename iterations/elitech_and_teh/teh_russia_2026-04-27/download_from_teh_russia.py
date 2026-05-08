from __future__ import annotations

import io
import re
from pathlib import Path

import pandas as pd
import requests
from PIL import Image
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent
INPUT_XLSX = BASE_DIR / "input" / "pictures.xlsx"
OUTPUT_DIR = BASE_DIR / "output"
IMPORT_DIR = OUTPUT_DIR / "import_images"
REPORT_XLSX = OUTPUT_DIR / "teh_russia_report.xlsx"
REMAINING_XLSX = OUTPUT_DIR / "remaining_after_teh_russia.xlsx"
SITE_ROOT = "https://teh-russia.ru"

ARTICLE_URLS = {
    "TPS728-B": "https://teh-russia.ru/catalog/akkumulyatornyy_instrument/akkumulyatory/1703/",
    "TAP12509-2": "https://teh-russia.ru/catalog/raskhodnye_materialy_i_sumki_dlya_instrumenta/raskhodnye_materialy/dlya_shlifmashin/dlya_ekstsentrikovykh_shlifmashin/2971/",
    "TAP15010-1": "https://teh-russia.ru/catalog/raskhodnye_materialy_i_sumki_dlya_instrumenta/raskhodnye_materialy/dlya_shlifmashin/dlya_ekstsentrikovykh_shlifmashin/2972/",
    "TV70L-29": "https://teh-russia.ru/catalog/raskhodnye_materialy_i_sumki_dlya_instrumenta/raskhodnye_materialy/dlya_pylesosov/osnastka_i_prisposobleniya_dlya_pylesosov/1858/",
    "TV20L-18": "https://teh-russia.ru/catalog/raskhodnye_materialy_i_sumki_dlya_instrumenta/raskhodnye_materialy/dlya_pylesosov/filtry/1699/",
    "TV30L-C-38": "https://teh-russia.ru/catalog/raskhodnye_materialy_i_sumki_dlya_instrumenta/raskhodnye_materialy/dlya_pylesosov/filtry/1854/",
    "TV20L-36": "https://teh-russia.ru/catalog/raskhodnye_materialy_i_sumki_dlya_instrumenta/raskhodnye_materialy/dlya_pylesosov/shlangi/1700/",
    "TS21509-1": "https://teh-russia.ru/catalog/raskhodnye_materialy_i_sumki_dlya_instrumenta/raskhodnye_materialy/dlya_shlifmashin/dlya_shlifmashin_po_betonu/1846/",
    "TS22513-2": "https://teh-russia.ru/catalog/raskhodnye_materialy_i_sumki_dlya_instrumenta/raskhodnye_materialy/dlya_shlifmashin/dlya_shlifmashin_po_betonu/1843/",
    "LPS508-01": "https://teh-russia.ru/catalog/akkumulyatornyy_instrument/shtangi_teleskopicheskie/1909/",
}


def norm_article(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", "", str(value).strip().upper())


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
            ),
            "Accept-Language": "ru,en;q=0.9",
        }
    )
    return s


def detect_article_col(df: pd.DataFrame) -> str:
    for col in df.columns:
        if "ARTIKUL" in str(col).upper():
            return col
    raise RuntimeError("Article column not found")


def safe_folder_name(article: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", article.strip())


def extract_images(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls = []

    for anchor in soup.select('a.detail-gallery-big__link[href]'):
        href = (anchor.get("href") or "").strip()
        if "/upload/" in href:
            urls.append(requests.compat.urljoin(SITE_ROOT, href))

    if not urls:
        for url in re.findall(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html):
            urls.append(url)

    unique = []
    seen = set()
    for url in urls:
        clean = url.split("?")[0]
        if clean not in seen:
            seen.add(clean)
            unique.append(clean)
    return unique


def save_webp(content: bytes, path: Path) -> bool:
    try:
        with Image.open(io.BytesIO(content)) as img:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            path.parent.mkdir(parents=True, exist_ok=True)
            img.save(path, "WEBP", quality=90, method=6)
        return True
    except Exception:
        return False


def download_image(session: requests.Session, url: str, destination: Path) -> bool:
    try:
        resp = session.get(url, timeout=30)
        if resp.status_code != 200:
            return False
        content_type = (resp.headers.get("Content-Type") or "").lower()
        if "image" not in content_type:
            return False
        return save_webp(resp.content, destination)
    except Exception:
        return False


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_excel(INPUT_XLSX)
    article_col = detect_article_col(df)
    session = make_session()

    rows = []
    for item in df.to_dict("records"):
        article = str(item[article_col]).strip()
        article_norm = norm_article(article)
        product_url = ARTICLE_URLS.get(article_norm, "")
        status = "FAIL"
        reason = "not_mapped"
        image_count = 0

        if product_url:
            try:
                page = session.get(product_url, timeout=30)
                if page.status_code == 200:
                    image_urls = extract_images(page.text)
                    folder = IMPORT_DIR / safe_folder_name(article)
                    saved = 0
                    for idx, image_url in enumerate(image_urls):
                        filename = "preview.webp" if idx == 0 else f"gallery_{idx:02d}.webp"
                        if download_image(session, image_url, folder / filename):
                            saved += 1
                    if saved:
                        status = "OK"
                        reason = ""
                        image_count = saved
                    else:
                        reason = "no_images"
                else:
                    reason = f"http_{page.status_code}"
            except Exception:
                reason = "request_error"

        rows.append(
            {
                article_col: article,
                "name": item.get("Наименование элемента", ""),
                "section": item.get("Название основного раздела", ""),
                "status": status,
                "reason": reason,
                "product_url": product_url,
                "image_count": image_count,
                "folder_name": safe_folder_name(article),
                "source": "teh-russia.ru",
            }
        )

    report = pd.DataFrame(rows)
    report.to_excel(REPORT_XLSX, index=False)

    confirmed = set()
    for folder in IMPORT_DIR.iterdir():
        if folder.is_dir() and (folder / "preview.webp").exists():
            confirmed.add(norm_article(folder.name))

    remaining = df[df[article_col].map(norm_article).map(lambda x: x not in confirmed)].copy()
    remaining.to_excel(REMAINING_XLSX, index=False)

    print(f"Input: {len(df)}")
    print(f"OK: {(report['status'] == 'OK').sum()}")
    print(f"Remaining: {len(remaining)}")


if __name__ == "__main__":
    main()
