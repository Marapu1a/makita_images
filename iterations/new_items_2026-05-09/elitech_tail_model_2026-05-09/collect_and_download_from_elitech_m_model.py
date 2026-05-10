from __future__ import annotations

import io
import re
import shutil
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests
from bs4 import BeautifulSoup
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
SOURCE_DIR = BASE_DIR.parent / "elitech" / "output"
INPUT_XLSX = SOURCE_DIR / "current_tail_after_manual_review.xlsx"
OUTPUT_DIR = BASE_DIR / "output"
IMPORT_DIR = OUTPUT_DIR / "import_images"
REPORT_XLSX = OUTPUT_DIR / "elitech_model_tail_report.xlsx"
REVIEW_XLSX = OUTPUT_DIR / "elitech_model_review.xlsx"
REMAINING_XLSX = OUTPUT_DIR / "remaining_after_elitech_model_tail.xlsx"


ARTICLE_RULES: dict[str, dict[str, object]] = {
    "155209": {"query": "155209", "mode": "exact_article"},
    "196375": {"query": "ЛН 5 Промо", "mode": "same_model", "title_any": ["ЛН 5 ПРОМО"]},
    "196376": {"query": "ЛН 5-ЗЕЛ Промо", "mode": "same_model", "title_any": ["ЛН 5-ЗЕЛ ПРОМО"]},
    "199936": {
        "query": "МШВ 0318Э Промо",
        "mode": "same_model",
        "title_any": ["МШВ 0318Э ПРОМО", "E2213.012.00"],
    },
    "205904": {"query": "ЛН 5/4В Промо", "mode": "same_model", "title_any": ["ЛН 5/4В ПРОМО"]},
    "205905": {"query": "П 1000ТВ", "mode": "same_model", "title_any": ["П 1000ТВ"]},
    "206451": {"query": "СПЛ 04-14", "mode": "same_model", "title_any": ["СПЛ 0414", "СПЛ 04-14"]},
    "191977": {"query": "191977", "mode": "exact_article"},
    "187850": {"query": "187850", "mode": "exact_article"},
    "185367": {"query": "185367", "mode": "exact_article"},
    "211368": {"query": "G 3000", "mode": "same_model", "title_any": ["G 3000"]},
    "202233": {"query": "БП 45/18 Prof", "mode": "review_variant"},
    "160682": {"query": "АИС 140СА", "mode": "review_missing"},
    "206444": {"query": "ВУ 25-10РЭ", "mode": "review_variant"},
    "203564": {"query": "ДА 20-2СЛ", "mode": "review_missing"},
    "201307": {"query": "КПМ 300/24 Промо", "mode": "review_missing"},
    "204449": {"query": "П 0724РЭМ Промо", "mode": "review_missing"},
    "207969": {"query": "ПЭ 08-20Р06", "mode": "review_variant"},
}


def norm_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def norm_article(value: object) -> str:
    return re.sub(r"\s+", "", norm_text(value).upper())


def token(value: object) -> str:
    return re.sub(r"[^A-ZА-Я0-9]+", "", norm_text(value).upper())


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


def search_elitech_m(session: requests.Session, query: str) -> list[tuple[str, str]]:
    url = (
        "https://elitech-m.ru/index.php?dispatch=products.search"
        "&subcats=Y&pshort=Y&pfull=Y&pname=Y&pkeywords=Y&search_performed=Y&q="
        f"{quote(query)}"
    )
    response = session.get(url, timeout=25)
    soup = BeautifulSoup(response.text, "html.parser")
    items: list[tuple[str, str]] = []
    seen: set[str] = set()
    for link in soup.select("a.product-title[href]"):
        href = link.get("href") or ""
        title = norm_text(link.get_text(" ", strip=True))
        if not href or href in seen:
            continue
        seen.add(href)
        items.append((title, href))
    return items


def fetch_product_meta(session: requests.Session, url: str) -> dict[str, str]:
    response = session.get(url, timeout=25)
    soup = BeautifulSoup(response.text, "html.parser")

    code = ""
    code_block = soup.select_one(".ty-product-block__code")
    if code_block:
        code_text = norm_text(code_block.get_text(" ", strip=True))
        match = re.search(r"([A-Z0-9-]{4,}|\d{6})", code_text.upper())
        code = match.group(1) if match else code_text

    image = ""
    og = soup.find("meta", attrs={"property": "og:image"})
    if og:
        image = og.get("content", "") or ""
        image = image.replace("https://elitech-m.ru:443https:/file.", "https://file.")
        image = image.replace(":443https:/file.", "://file.")
        if image.startswith("https://elitech-m.ru:443/"):
            image = image.replace("https://elitech-m.ru:443/", "https://")

    gallery_urls: list[str] = []
    seen: set[str] = set()
    for tag in soup.select("img[src], a[href], source[srcset]"):
        raw_value = tag.get("src") or tag.get("href") or tag.get("srcset") or ""
        value = raw_value.split(",")[0].strip()
        if "/images/" not in value or "/thumbnails/" not in value:
            continue
        if "/detailed/" not in value:
            continue
        value = re.sub(r"/thumbnails/\d+/\d+/", "/", value)
        if value not in seen:
            seen.add(value)
            gallery_urls.append(value)

    return {
        "candidate_code": code,
        "candidate_image": image,
        "gallery_urls": "\n".join(gallery_urls),
    }


def is_detailed_image(url: str) -> bool:
    low = url.lower()
    return "/images/detailed/" in low and "logo" not in low


def select_candidate(article: str, rule: dict[str, object], search_results: list[tuple[str, str]]) -> dict[str, str]:
    mode = str(rule.get("mode", "review_missing"))
    wanted_fragments = [token(x) for x in rule.get("title_any", [])]
    article_t = token(article)

    for title, href in search_results:
        title_t = token(title)
        if mode == "exact_article" and article_t in title_t:
            return {"candidate_title": title, "candidate_url": href, "status": "safe_exact_article"}
        if mode == "same_model" and any(fragment and fragment in title_t for fragment in wanted_fragments):
            return {"candidate_title": title, "candidate_url": href, "status": "safe_model_family"}
        if mode == "review_variant" and title:
            return {"candidate_title": title, "candidate_url": href, "status": "review_variant"}

    fallback_status = "review_missing" if mode.startswith("review") else "no_hit"
    return {"candidate_title": "", "candidate_url": "", "status": fallback_status}


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

    try:
        folder = IMPORT_DIR / safe_folder_name(article)
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True, exist_ok=True)

        saved = 0
        seen: set[str] = set()
        for index, image_url in enumerate(image_urls, start=1):
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
            ok = save_webp(response.content, folder / filename)
            if ok:
                saved += 1

        if saved == 0:
            shutil.rmtree(folder, ignore_errors=True)
            return 0, "save_failed"
        return saved, ""
    except Exception as exc:
        return 0, str(exc)[:120]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(INPUT_XLSX)
    article_col = detect_article_col(df)
    session = make_session()

    rows: list[dict[str, object]] = []
    for row in df.to_dict("records"):
        article = norm_article(row[article_col])
        name = norm_text(row.get("Наименование элемента", ""))
        rule = ARTICLE_RULES.get(article, {"query": article, "mode": "review_missing"})
        query = str(rule.get("query", article))

        search_results = search_elitech_m(session, query)
        chosen = select_candidate(article, rule, search_results)
        candidate_url = chosen["candidate_url"]
        candidate_title = chosen["candidate_title"]
        candidate_status = chosen["status"]
        candidate_code = ""
        candidate_image = ""
        gallery_urls: list[str] = []
        download_status = "SKIP"
        download_note = ""
        image_count = 0

        if candidate_url:
            meta = fetch_product_meta(session, candidate_url)
            candidate_code = meta["candidate_code"]
            candidate_image = meta["candidate_image"]
            gallery_urls = [x for x in str(meta.get("gallery_urls", "")).splitlines() if x]

        effective_urls = gallery_urls.copy()
        if is_detailed_image(candidate_image) and candidate_image not in effective_urls:
            effective_urls.insert(0, candidate_image)

        safe_download = candidate_status in {"safe_exact_article", "safe_model_family"} and bool(effective_urls)
        if safe_download:
            saved_count, note = download_images(session, effective_urls, article)
            if saved_count:
                download_status = "OK"
                image_count = saved_count
            else:
                download_status = "FAIL"
                download_note = note
        elif candidate_status.startswith("safe_") and (candidate_image or gallery_urls):
            download_status = "REVIEW"
            download_note = "candidate_image_not_detailed"
        else:
            download_status = "REVIEW" if candidate_status.startswith("review") else "FAIL"
            download_note = candidate_status

        rows.append(
            {
                article_col: article,
                "name": name,
                "query": query,
                "candidate_status": candidate_status,
                "candidate_title": candidate_title,
                "candidate_url": candidate_url,
                "candidate_code": candidate_code,
                "candidate_image": candidate_image,
                "gallery_found": len(gallery_urls),
                "download_status": download_status,
                "download_note": download_note,
                "image_count": image_count,
                "source": "elitech-m.ru model tail",
            }
        )

    report = pd.DataFrame(rows)
    report.to_excel(REPORT_XLSX, index=False)

    review = report[report["download_status"] == "REVIEW"].copy()
    review.to_excel(REVIEW_XLSX, index=False)

    confirmed = set()
    for folder in IMPORT_DIR.iterdir():
        if folder.is_dir() and (folder / "preview.webp").exists():
            confirmed.add(norm_article(folder.name))

    remaining = df[df[article_col].map(norm_article).map(lambda value: value not in confirmed)].copy()
    remaining.to_excel(REMAINING_XLSX, index=False)

    print(f"Input: {len(df)}")
    print(f"Downloaded: {len(confirmed)}")
    print(f"Review: {(report['download_status'] == 'REVIEW').sum()}")
    print(f"Remaining: {len(remaining)}")


if __name__ == "__main__":
    main()
