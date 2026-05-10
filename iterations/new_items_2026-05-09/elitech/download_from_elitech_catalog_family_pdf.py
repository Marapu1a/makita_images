from __future__ import annotations

import re
from pathlib import Path

import fitz
import pandas as pd
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
INPUT_XLSX = BASE_DIR / "output" / "remaining_after_elitech_catalog_pdf.xlsx"
OUTPUT_DIR = BASE_DIR / "output"
IMPORT_DIR = OUTPUT_DIR / "import_images"
REPORT_XLSX = OUTPUT_DIR / "elitech_catalog_family_pdf_report.xlsx"
REMAINING_XLSX = OUTPUT_DIR / "remaining_after_elitech_catalog_family_pdf.xlsx"
PDF_PATH = BASE_DIR / "work" / "ELITECH_2025_katalog.pdf"

FAMILY_MAP = {
    "drill_family": {
        "articles": ["191611", "198041", "202413", "204842", "211351"],
        "page": 57,
        "keyword": "Дрель аккумуляторная",
        "rect_index": 0,
    },
    "laser_family": {
        "articles": ["199635", "200569"],
        "page": 110,
        "keyword": "Нивелир лазерный",
        "rect_index": 0,
    },
    "welding_family": {
        "articles": ["201315", "203958"],
        "page": 158,
        "keyword": "Сварочный инвертор",
        "rect_index": 0,
    },
    "chainsaw_family": {
        "articles": ["202236"],
        "page": 92,
        "keyword": "Пила цепная бензиновая",
        "rect_index": 0,
    },
    "oil_4td_family": {
        "articles": ["200363", "200364", "200366"],
        "page": 230,
        "keyword": "4ТD",
        "rect_index": 1,
    },
    "oil_compressor_family": {
        "articles": ["200361"],
        "page": 230,
        "keyword": "КМ100",
        "rect_index": 0,
    },
    "disc_metal_family": {
        "articles": ["198544", "184658", "184660", "184662", "184664", "184666", "184670", "198551"],
        "page": 203,
        "keyword": "по металлу",
        "rect_index": 0,
    },
    "disc_stone_family": {
        "articles": ["198552", "198553", "198554", "198555", "198556"],
        "page": 204,
        "keyword": "сегментные",
        "rect_index": 0,
    },
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


def pick_image_rect(page: fitz.Page, keyword: str, rect_index: int) -> fitz.Rect | None:
    rects = page.search_for(keyword)
    if not rects:
        return None
    target = rects[min(rect_index, len(rects) - 1)]
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


def render_clip(page: fitz.Page, clip: fitz.Rect, dest_webp: Path) -> bool:
    try:
        padded = fitz.Rect(
            max(0, clip.x0 - 10),
            max(0, clip.y0 - 10),
            min(page.rect.x1, clip.x1 + 10),
            min(page.rect.y1, clip.y1 + 10),
        )
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=padded, alpha=False)
        temp_png = dest_webp.with_suffix(".png")
        dest_webp.parent.mkdir(parents=True, exist_ok=True)
        pix.save(temp_png)
        with Image.open(temp_png) as img:
            img.save(dest_webp, "WEBP", quality=92, method=6)
        temp_png.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def build_family_images(doc: fitz.Document) -> dict[str, Path]:
    generated: dict[str, Path] = {}
    work_dir = BASE_DIR / "work" / "family_previews"
    work_dir.mkdir(parents=True, exist_ok=True)
    for family_name, payload in FAMILY_MAP.items():
        page = doc[payload["page"] - 1]
        rect = pick_image_rect(page, payload["keyword"], payload["rect_index"])
        if not rect:
            continue
        out = work_dir / f"{family_name}.webp"
        if render_clip(page, rect, out):
            generated[family_name] = out
    return generated


def family_for_article(article: str) -> str | None:
    for family_name, payload in FAMILY_MAP.items():
        if article in payload["articles"]:
            return family_name
    return None


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_excel(INPUT_XLSX)
    article_col = detect_article_col(df)
    df["_article_norm"] = df[article_col].map(norm_article)

    doc = fitz.open(PDF_PATH)
    family_images = build_family_images(doc)

    rows = []
    for row in df.to_dict("records"):
        article = str(row[article_col]).strip()
        article_norm = row["_article_norm"]
        family_name = family_for_article(article_norm)
        status = "FAIL"
        reason = "no_family_match"

        if family_name and family_name in family_images:
            src = family_images[family_name]
            folder = IMPORT_DIR / safe_folder_name(article)
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "preview.webp").write_bytes(src.read_bytes())
            status = "OK"
            reason = ""

        rows.append(
            {
                article_col: article,
                "name": row.get("Наименование элемента", ""),
                "status": status,
                "reason": reason,
                "family_name": family_name or "",
                "source": "ELITECH_2025_katalog.pdf family",
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
