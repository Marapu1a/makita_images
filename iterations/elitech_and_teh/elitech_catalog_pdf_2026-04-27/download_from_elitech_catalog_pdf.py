from __future__ import annotations

import re
from pathlib import Path

import fitz
import pandas as pd
import requests
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
INPUT_XLSX = BASE_DIR / "input" / "pictures.xlsx"
OUTPUT_DIR = BASE_DIR / "output"
IMPORT_DIR = OUTPUT_DIR / "import_images"
REPORT_XLSX = OUTPUT_DIR / "elitech_catalog_pdf_report.xlsx"
REMAINING_XLSX = OUTPUT_DIR / "remaining_after_elitech_catalog_pdf.xlsx"
PDF_URL = "https://elitech.ru/upload/iblock/95b/nc81nxsh73y1b0ij1c1naap2l5852ep7/ELITECH_2025_katalog.pdf"
PDF_PATH = BASE_DIR / "work" / "ELITECH_2025_katalog.pdf"


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


def download_pdf() -> None:
    if PDF_PATH.exists():
        return
    PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(PDF_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
    resp.raise_for_status()
    PDF_PATH.write_bytes(resp.content)


def find_pages(doc: fitz.Document, articles: set[str]) -> dict[str, int]:
    found: dict[str, int] = {}
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        for article in articles:
            if article not in found and article in text:
                found[article] = page_num
    return found


def pick_nearest_image(page: fitz.Page, article: str) -> fitz.Rect | None:
    text_rects = page.search_for(article)
    if not text_rects:
        return None
    target = text_rects[0]
    infos = page.get_image_info(xrefs=True)
    if not infos:
        return None

    def distance(info: dict) -> tuple[float, float]:
        bbox = fitz.Rect(info["bbox"])
        dy = 0.0
        if bbox.y1 < target.y0:
            dy = target.y0 - bbox.y1
        elif bbox.y0 > target.y1:
            dy = bbox.y0 - target.y1
        dx = abs(bbox.x0 - target.x0)
        return (dy, dx)

    best = min(infos, key=distance)
    return fitz.Rect(best["bbox"])


def render_clip(page: fitz.Page, clip: fitz.Rect, destination: Path) -> bool:
    try:
        padded = fitz.Rect(
            max(0, clip.x0 - 10),
            max(0, clip.y0 - 10),
            min(page.rect.x1, clip.x1 + 10),
            min(page.rect.y1, clip.y1 + 10),
        )
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=padded, alpha=False)
        destination.parent.mkdir(parents=True, exist_ok=True)
        pix.save(destination)
        with Image.open(destination) as img:
            img.save(destination.with_suffix(".webp"), "WEBP", quality=92, method=6)
        destination.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    download_pdf()

    df = pd.read_excel(INPUT_XLSX)
    article_col = detect_article_col(df)
    df = df[df["Название основного раздела"].astype(str).str.strip().eq("Elitech")].copy()
    df["_article_norm"] = df[article_col].map(norm_article)
    articles = set(df["_article_norm"].tolist())

    doc = fitz.open(PDF_PATH)
    article_pages = find_pages(doc, articles)

    rows: list[dict] = []
    for row in df.to_dict("records"):
        article = str(row[article_col]).strip()
        article_norm = row["_article_norm"]
        page_num = article_pages.get(article_norm)
        status = "FAIL"
        reason = "not_found_in_pdf"

        if page_num:
            page = doc[page_num - 1]
            clip = pick_nearest_image(page, article_norm)
            if clip:
                folder = IMPORT_DIR / safe_folder_name(article)
                png_temp = folder / "preview.png"
                if render_clip(page, clip, png_temp):
                    status = "OK"
                    reason = ""
                else:
                    reason = "render_failed"
            else:
                reason = "image_not_found"

        rows.append(
            {
                article_col: article,
                "name": row.get("Наименование элемента", ""),
                "status": status,
                "reason": reason,
                "page_num": page_num or "",
                "folder_name": safe_folder_name(article),
                "source": "ELITECH_2025_katalog.pdf",
            }
        )

    report = pd.DataFrame(rows)
    report.to_excel(REPORT_XLSX, index=False)

    confirmed = set()
    for folder in IMPORT_DIR.iterdir():
        if folder.is_dir() and (folder / "preview.webp").exists():
            confirmed.add(norm_article(folder.name))

    remaining = df[df["_article_norm"].map(lambda value: value not in confirmed)].drop(columns=["_article_norm"])
    remaining.to_excel(REMAINING_XLSX, index=False)

    print(f"Input: {len(df)}")
    print(f"OK: {(report['status'] == 'OK').sum()}")
    print(f"Remaining: {len(remaining)}")


if __name__ == "__main__":
    main()
