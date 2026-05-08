from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent
INPUT_XLSX = BASE_DIR / "input" / "pictures.xlsx"
OUTPUT_XLSX = BASE_DIR / "output" / "elitech_m_candidates.xlsx"


def norm_article(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", "", str(value).strip().upper())


def detect_article_col(df: pd.DataFrame) -> str:
    for col in df.columns:
        if "ARTIKUL" in str(col).upper():
            return col
    raise RuntimeError("Article column not found")


def classify(article: str, title: str, code: str) -> str:
    if not title:
        return "no_hit"
    title_u = title.upper()
    code_u = code.upper()
    if article == code_u:
        if "WERT" in title_u:
            return "suspicious_wert"
        if "ПРОМОКОМПЛЕКТ" in title_u:
            return "exact_promo"
        return "exact"
    if article in title_u:
        return "suspicious_title_only"
    return "suspicious_other"


def main() -> None:
    df = pd.read_excel(INPUT_XLSX)
    article_col = detect_article_col(df)
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

    rows = []
    for row in df.to_dict("records"):
        article = norm_article(row[article_col])
        search_url = (
            "https://elitech-m.ru/index.php?dispatch=products.search"
            "&subcats=Y&pshort=Y&pfull=Y&pname=Y&pkeywords=Y&search_performed=Y&q="
            f"{article}"
        )
        r = s.get(search_url, timeout=25)
        soup = BeautifulSoup(r.text, "html.parser")

        href = ""
        title = ""
        image = ""
        code = ""

        for a in soup.select("a.product-title[href]"):
            href = a.get("href") or ""
            title = a.get_text(" ", strip=True)
            if href:
                break

        if href:
            pr = s.get(href, timeout=25)
            psoup = BeautifulSoup(pr.text, "html.parser")
            code_block = psoup.select_one(".ty-product-block__code")
            if code_block:
                code_text = code_block.get_text(" ", strip=True)
                m = re.search(r"([A-Z0-9\\-]{4,}|\\d{6})", code_text.upper())
                code = m.group(1) if m else code_text
            og_tag = psoup.find("meta", attrs={"property": "og:image"})
            if og_tag:
                image = og_tag.get("content", "")
                image = image.replace(":443https:/file.", "://file.")
                image = image.replace("https://elitech-m.ru:443https:/file.", "https://file.")
                if image.startswith("https://elitech-m.ru:443/"):
                    image = image.replace("https://elitech-m.ru:443/", "https://")

        rows.append(
            {
                article_col: article,
                "name": row.get("Наименование элемента", ""),
                "candidate_url": href,
                "candidate_title": title,
                "candidate_code": code,
                "candidate_image": image,
                "candidate_status": classify(article, title, code),
                "source": "elitech-m.ru",
            }
        )

    out = pd.DataFrame(rows)
    OUTPUT_XLSX.parent.mkdir(parents=True, exist_ok=True)
    out.to_excel(OUTPUT_XLSX, index=False)
    print(out["candidate_status"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
