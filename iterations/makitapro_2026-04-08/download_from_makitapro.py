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
SLEEP_BETWEEN_ITEMS = 0.2
MAX_GALLERY = 5
MIN_BYTES = 1000
DOWNLOAD_RETRIES = 2
RETRY_SLEEP = 0.5
FETCH_RETRIES = 2

WEBP_QUALITY = 82
WEBP_METHOD = 6
MAX_WIDTH = 1600
MAX_HEIGHT = 1600

Image.MAX_IMAGE_PIXELS = None


def is_empty(value) -> bool:
    if pd.isna(value):
        return True
    text = str(value).strip()
    return text == "" or text.lower() == "nan"


def normalize_article(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().upper()
    return re.sub(r"\s+", "", text)


def contains_exact_article(text: str, article: str) -> bool:
    if not text or not article:
        return False
    pattern = rf"(?<![A-Z0-9]){re.escape(article.upper())}(?![A-Z0-9])"
    return re.search(pattern, text.upper()) is not None


def is_clean_base_title(title: str) -> int:
    bad_patterns = [
        r"\bPROMO\b",
        r"\bУЦЕН",
        r"\bБЕЗ\b",
        r"\bКОМПЛЕКТ\b",
        r"\bНАБОР\b",
        r"\bПАКЕТ",
        r"\bПОДАР",
    ]
    upper_title = title.upper()
    return 0 if any(re.search(pattern, upper_title) for pattern in bad_patterns) else 1


def normalize_text(value: object) -> str:
    text = str(value).strip().upper()
    text = text.replace("Ё", "Е")
    text = re.sub(r"\s+", " ", text)
    return text


def token_overlap_score(left: str, right: str) -> int:
    stopwords = {"MAKITA", "ДЛЯ", "И", "С", "В", "НА", "ПО", "ЦЕНА", "ОТЗЫВЫ", "ФОТО"}
    left_tokens = {token for token in re.findall(r"[A-ZА-Я0-9-]+", left.upper()) if len(token) > 1 and token not in stopwords}
    right_tokens = {token for token in re.findall(r"[A-ZА-Я0-9-]+", right.upper()) if len(token) > 1 and token not in stopwords}
    return len(left_tokens & right_tokens)


def safe_name(value: object) -> str:
    text = str(value).strip()
    text = re.sub(r"[^\w\-.]+", "_", text)
    return text[:120]


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
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


def search_products(article: str, session: requests.Session) -> list[tuple[str, str]]:
    url = SEARCH_URL.format(query=quote_plus(article))
    text = fetch_text(url, session)
    soup = BeautifulSoup(text, "html.parser")

    skip_titles = {"", "ВЕС, КГ", "ПРОИЗВОДИТЕЛЬ", "ЦЕНА", "ОТЗЫВЫ"}
    candidates_map: dict[str, str] = {}

    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        title = " ".join(link.get_text(" ", strip=True).split())

        if not re.search(r"-i\d+\.html$", href):
            continue

        full_url = urljoin(BASE_URL, href)
        title_upper = title.upper()
        current_title = candidates_map.get(full_url, "")

        if title_upper in skip_titles:
            title = ""

        if len(title) > len(current_title):
            candidates_map[full_url] = title

    candidates = [(url, title) for url, title in candidates_map.items()]

    return candidates


def extract_product_images(product_url: str, session: requests.Session) -> tuple[str, list[str]]:
    text = fetch_text(product_url, session)

    title_match = re.search(r"<title>(.*?)</title>", text, re.S | re.I)
    title = title_match.group(1).strip() if title_match else ""

    id_match = re.search(r"-i(\d+)\.html$", product_url)
    if not id_match:
        return title, []

    product_id = id_match.group(1)
    image_matches = re.findall(
        r"/u/catalog/[^\"'\s<>]+?\.(?:jpg|jpeg|png|webp|JPG|JPEG|PNG|WEBP)",
        text,
        flags=re.I,
    )

    image_urls: list[str] = []
    for rel_url in image_matches:
        if f"/{product_id}" not in rel_url:
            continue
        full_url = urljoin(BASE_URL, rel_url)
        if full_url not in image_urls:
            image_urls.append(full_url)

    def sort_key(url: str) -> tuple[int, int, str]:
        lower = url.lower()
        is_large = 0 if "large" in lower else 1
        is_thumb = 1 if "thumbnail" in lower or "x300" in lower or "-300" in lower else 0
        return (is_large, is_thumb, lower)

    image_urls = sorted(image_urls, key=sort_key)
    return title, image_urls


def choose_best_candidate(article: str, name: str, candidates: list[tuple[str, str]], session: requests.Session) -> tuple[str | None, str, list[str], str]:
    article_norm = normalize_article(article)
    name_norm = normalize_text(name)

    scored: list[tuple[tuple[int, int, int, int], str, str, list[str]]] = []

    for product_url, title_hint in candidates[:20]:
        try:
            page_title, image_urls = extract_product_images(product_url, session)
        except Exception:
            continue

        effective_title = page_title or title_hint or ""
        title_norm = normalize_text(effective_title)
        hint_norm = normalize_text(title_hint)
        article_in_title = 1 if contains_exact_article(effective_title, article_norm) else 0
        clean_base_title = is_clean_base_title(effective_title)
        has_images = 1 if image_urls else 0
        has_plus = 0 if "+" in effective_title else 1
        title_overlap = 1 if title_norm and title_norm in name_norm else 0
        hint_overlap = token_overlap_score(hint_norm, name_norm)
        shorter_title = -len(effective_title)

        score = (article_in_title, hint_overlap, clean_base_title, title_overlap, has_images, has_plus, shorter_title)
        scored.append((score, product_url, effective_title, image_urls))

    if not scored:
        return None, "", [], "not_found"

    scored.sort(reverse=True)
    best_score, best_url, best_title, best_images = scored[0]

    match_type = "title_article_match" if best_score[0] else "fallback"
    if contains_exact_article(best_title, article_norm):
        match_type = "exact_article_in_title"

    return best_url, best_title, best_images, match_type


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

    saved_preview = False
    saved_gallery = 0
    fail_reason = ""

    preview_ok, preview_reason = download_and_compress_image(image_urls[0], item_dir / "preview.webp", session)
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


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(INPUT_FILE)

    required_columns = [COL_ARTICLE, COL_NAME]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    report_rows: list[dict] = []

    ok_count = 0
    fail_count = 0
    skip_count = 0

    with make_session() as session:
        total = len(df)

        for index, row in df.iterrows():
            article = str(row.get(COL_ARTICLE, "")).strip()
            name = str(row.get(COL_NAME, "")).strip()

            print(f"[{index + 1}/{total}] {article} | {name}")

            if is_empty(article):
                skip_count += 1
                report_rows.append(
                    {
                        "article": article,
                        "name": name,
                        "source_name": SOURCE_NAME,
                        "search_url": "",
                        "product_url": "",
                        "match_type": "",
                        "status": "SKIP",
                        "images_found": 0,
                        "gallery_saved": 0,
                        "note": "empty_article",
                    }
                )
                continue

            search_url = SEARCH_URL.format(query=quote_plus(article))

            try:
                candidates = search_products(article, session)
                product_url, product_title, image_urls, match_type = choose_best_candidate(article, name, candidates, session)
            except Exception as exc:
                fail_count += 1
                report_rows.append(
                    {
                        "article": article,
                        "name": name,
                        "source_name": SOURCE_NAME,
                        "search_url": search_url,
                        "product_url": "",
                        "match_type": "",
                        "status": "FAIL",
                        "images_found": 0,
                        "gallery_saved": 0,
                        "note": f"search_error:{exc}",
                    }
                )
                continue

            if not product_url:
                fail_count += 1
                report_rows.append(
                    {
                        "article": article,
                        "name": name,
                        "source_name": SOURCE_NAME,
                        "search_url": search_url,
                        "product_url": "",
                        "match_type": "",
                        "status": "FAIL",
                        "images_found": 0,
                        "gallery_saved": 0,
                        "note": "product_not_found",
                    }
                )
                time.sleep(SLEEP_BETWEEN_ITEMS)
                continue

            ok, gallery_saved, note = save_product_images(article, image_urls, session)
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
                    "search_url": search_url,
                    "product_url": product_url,
                    "match_type": match_type,
                    "status": status,
                    "images_found": len(image_urls),
                    "gallery_saved": gallery_saved,
                    "note": note,
                }
            )

            time.sleep(SLEEP_BETWEEN_ITEMS)

    report_df = pd.DataFrame(report_rows)
    report_df.to_excel(REPORT_FILE, index=False)

    print("\n=== MAKITAPRO DOWNLOAD SUMMARY ===")
    print(f"Input rows: {len(df)}")
    print(f"OK: {ok_count}")
    print(f"FAIL: {fail_count}")
    print(f"SKIP: {skip_count}")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
