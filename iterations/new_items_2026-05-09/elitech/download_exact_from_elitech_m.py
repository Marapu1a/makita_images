from __future__ import annotations

import io
import re
from pathlib import Path

import pandas as pd
import requests
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
INPUT_XLSX = BASE_DIR / "output" / "remaining_after_elitech_m_exact.xlsx"
CANDIDATES_XLSX = BASE_DIR / "output" / "elitech_m_candidates.xlsx"
OUTPUT_DIR = BASE_DIR / "output"
IMPORT_DIR = OUTPUT_DIR / "import_images"
REPORT_XLSX = OUTPUT_DIR / "elitech_m_report.xlsx"
REMAINING_XLSX = OUTPUT_DIR / "remaining_after_elitech_m.xlsx"

APPROVED_ARTICLES: set[str] = set()

FAMILY_IMAGE_SOURCE = {
    "201948": "201952",
    "201956": "201952",
}


def norm_article(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", "", str(value).strip().upper())


def detect_article_col(df: pd.DataFrame) -> str:
    for col in df.columns:
        if "ARTIKUL" in str(col).upper():
            return col
    raise RuntimeError("Article column not found")


def safe_folder_name(article: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", article.strip())


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


def save_webp(content: bytes, destination: Path) -> bool:
    try:
        with Image.open(io.BytesIO(content)) as img:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            destination.parent.mkdir(parents=True, exist_ok=True)
            img.save(destination, "WEBP", quality=92, method=6)
        return True
    except Exception:
        return False


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(INPUT_XLSX)
    candidates = pd.read_excel(CANDIDATES_XLSX)
    article_col = detect_article_col(df)
    session = make_session()
    approved_articles = set()
    for row in candidates.to_dict("records"):
        status = str(row.get("candidate_status", "")).strip()
        image_url = str(row.get("candidate_image") or "")
        if status == "exact" or (status == "suspicious_wert" and "/images/detailed/" in image_url):
            approved_articles.add(norm_article(row[article_col]))

    candidate_map = {
        norm_article(row[article_col]): row
        for row in candidates.to_dict("records")
    }

    rows = []
    for row in df.to_dict("records"):
        article = str(row[article_col]).strip()
        article_norm = norm_article(article)
        cand = candidate_map.get(article_norm)
        status = "FAIL"
        reason = "not_approved"
        image_count = 0
        candidate_url = ""

        if cand:
            candidate_url = str(cand.get("candidate_url") or "")
            if article_norm in approved_articles and candidate_url:
                image_url = str(cand.get("candidate_image") or "")
                if image_url:
                    try:
                        r = session.get(image_url, timeout=30)
                        if r.status_code == 200 and "image" in (r.headers.get("Content-Type") or "").lower():
                            folder = IMPORT_DIR / safe_folder_name(article)
                            if save_webp(r.content, folder / "preview.webp"):
                                status = "OK"
                                reason = ""
                                image_count = 1
                            else:
                                reason = "save_failed"
                        else:
                            reason = f"image_http_{r.status_code}"
                    except Exception:
                        reason = "request_error"
                else:
                    reason = "no_candidate_image"

        if status == "FAIL" and article_norm in FAMILY_IMAGE_SOURCE:
            src_article = FAMILY_IMAGE_SOURCE[article_norm]
            src_folder = IMPORT_DIR / safe_folder_name(src_article)
            src_preview = src_folder / "preview.webp"
            if src_preview.exists():
                folder = IMPORT_DIR / safe_folder_name(article)
                folder.mkdir(parents=True, exist_ok=True)
                (folder / "preview.webp").write_bytes(src_preview.read_bytes())
                status = "OK"
                reason = ""
                image_count = 1

        rows.append(
            {
                article_col: article,
                "name": row.get("Наименование элемента", ""),
                "candidate_url": candidate_url,
                "status": status,
                "reason": reason,
                "image_count": image_count,
                "source": "elitech-m.ru",
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
    print(f"OK: {(report['status'] == 'OK').sum()}")
    print(f"Remaining: {len(remaining)}")


if __name__ == "__main__":
    main()
