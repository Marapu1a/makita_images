from __future__ import annotations

import io
import re
import shutil
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
SOURCE_XLSX = (
    BASE_DIR.parent / "elitech_tail_model_2026-05-09" / "output" / "remaining_after_elitech_model_tail.xlsx"
)
OUTPUT_DIR = BASE_DIR / "output"
IMPORT_DIR = OUTPUT_DIR / "import_images"
REPORT_XLSX = OUTPUT_DIR / "elitech_tail_exact_report.xlsx"
REMAINING_XLSX = OUTPUT_DIR / "remaining_after_elitech_tail_exact.xlsx"


EXACT_URLS: dict[str, dict[str, object]] = {
    "160682": {
        "mode": "direct",
        "source": "vseinstrumenti.ru exact image",
        "urls": [
            "https://cdn.vseinstrumenti.ru/images/goods/stroitelnyj-instrument/svarochnoe-oborudovanie/92879/560x504/52972890.jpg",
        ],
    },
    "201307": {
        "mode": "direct",
        "source": "makitapro.ru exact product page",
        "urls": [
            "https://www.makitapro.ru/u/catalog/17006_large-.jpg",
        ],
    },
    "202233": {
        "mode": "direct",
        "source": "invoz.ru exact product page",
        "urls": [
            "https://www.invoz.ru/upload/iblock/91e/dhe0osk7nsv3xndwmi73srtipmjujgx4/pila_tsepnaya_benzinovaya_elitech_bp_45_18_prof_202233.jpeg",
        ],
    },
    "204449": {
        "mode": "direct",
        "source": "makitapro.ru exact product page",
        "urls": [
            "https://www.makitapro.ru/u/catalog/17223_large-.jpg",
        ],
    },
    "206444": {
        "mode": "elitech_m_gallery",
        "source": "elitech-m.ru near-family variant",
        "page": "https://elitech-m.ru/item-id-1860656/",
    },
    "203564": {
        "mode": "direct",
        "source": "piterinstrument.ru exact product page",
        "urls": [
            "https://piterinstrument.ru/upload/yml/elitech/203/203564_00.jpg.webp",
        ],
    },
    "207969": {
        "mode": "makita_profi_gallery",
        "source": "makita-profi.ru exact product page",
        "page": "https://makita-profi.ru/plitkorez-elektricheskij-pe-08-20r06-e200801500/",
    },
}


def norm_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def norm_article(value: object) -> str:
    return re.sub(r"\s+", "", norm_text(value).upper())


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


def save_webp(content: bytes, destination: Path) -> bool:
    try:
        with Image.open(io.BytesIO(content)) as img:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            img.thumbnail((1600, 1600), Image.LANCZOS)
            destination.parent.mkdir(parents=True, exist_ok=True)
            img.save(destination, "WEBP", quality=92, method=6)
        return True
    except Exception:
        return False


def download_images(session: requests.Session, image_urls: list[str], article: str) -> tuple[int, str]:
    if not image_urls:
        return 0, "no_images"

    folder = IMPORT_DIR / safe_folder_name(article)
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=True)

    saved = 0
    seen: set[str] = set()
    try:
        for image_url in image_urls:
            if image_url in seen:
                continue
            seen.add(image_url)
            response = session.get(image_url, timeout=30)
            if response.status_code != 200:
                continue
            ctype = (response.headers.get("Content-Type") or "").lower()
            if "image" not in ctype:
                continue
            filename = "preview.webp" if saved == 0 else f"gallery_{saved:02d}.webp"
            if save_webp(response.content, folder / filename):
                saved += 1
        if saved == 0:
            shutil.rmtree(folder, ignore_errors=True)
            return 0, "save_failed"
        return saved, ""
    except Exception as exc:
        shutil.rmtree(folder, ignore_errors=True)
        return 0, str(exc)[:120]


def parse_elitech_m_gallery(session: requests.Session, page_url: str) -> list[str]:
    response = session.get(page_url, timeout=25)
    soup = BeautifulSoup(response.text, "html.parser")
    urls: list[str] = []
    seen: set[str] = set()
    for tag in soup.select("img[src], a[href], source[srcset]"):
        raw_value = tag.get("src") or tag.get("href") or tag.get("srcset") or ""
        value = raw_value.split(",")[0].strip()
        if "/images/" not in value or "/thumbnails/" not in value or "/detailed/" not in value:
            continue
        value = re.sub(r"/thumbnails/\d+/\d+/", "/", value)
        if value not in seen:
            seen.add(value)
            urls.append(value)
    return urls


def parse_makita_profi_gallery(session: requests.Session, page_url: str, article: str) -> list[str]:
    response = session.get(page_url, timeout=25)
    pattern = re.compile(
        rf"https://makita-profi\.ru/image/cache/image/catalog/elitech_images/{re.escape(article)}_\d+-800x800\.jpg",
        re.I,
    )
    urls: list[str] = []
    seen: set[str] = set()
    for match in pattern.finditer(response.text):
        url = match.group(0)
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def gather_urls(session: requests.Session, article: str, rule: dict[str, object]) -> list[str]:
    mode = str(rule["mode"])
    if mode == "direct":
        return [str(x) for x in rule.get("urls", [])]
    if mode == "elitech_m_gallery":
        return parse_elitech_m_gallery(session, str(rule["page"]))
    if mode == "makita_profi_gallery":
        return parse_makita_profi_gallery(session, str(rule["page"]), article)
    return []


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(SOURCE_XLSX)
    article_col = detect_article_col(df)
    session = make_session()

    rows: list[dict[str, object]] = []
    for row in df.to_dict("records"):
        article = norm_article(row[article_col])
        name = norm_text(row.get("Наименование элемента", ""))
        rule = EXACT_URLS.get(article)

        source = ""
        url_count = 0
        status = "SKIP"
        note = "no_rule"
        image_count = 0

        if rule:
            source = str(rule["source"])
            urls = gather_urls(session, article, rule)
            url_count = len(urls)
            if urls:
                saved, note = download_images(session, urls, article)
                if saved:
                    status = "OK"
                    image_count = saved
                    note = ""
                else:
                    status = "FAIL"
            else:
                status = "FAIL"
                note = "no_images"

        rows.append(
            {
                article_col: article,
                "name": name,
                "source": source,
                "candidate_urls": url_count,
                "download_status": status,
                "download_note": note,
                "image_count": image_count,
            }
        )

    report = pd.DataFrame(rows)
    report.to_excel(REPORT_XLSX, index=False)

    confirmed = set()
    for folder in IMPORT_DIR.iterdir():
        if folder.is_dir() and (folder / "preview.webp").exists():
            confirmed.add(norm_article(folder.name))

    remaining = df[df[article_col].map(norm_article).map(lambda value: value not in confirmed)].copy()
    remaining.to_excel(REMAINING_XLSX, index=False)

    print(f"Input: {len(df)}")
    print(f"Downloaded: {len(confirmed)}")
    print(f"Remaining: {len(remaining)}")


if __name__ == "__main__":
    main()
