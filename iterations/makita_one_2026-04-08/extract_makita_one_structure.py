from __future__ import annotations

from pathlib import Path
import re

import pandas as pd
import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "work" / "makita_one_structure.xlsx"
BASE_URL = "https://makita.one"
CATALOG_URL = BASE_URL + "/catalog/"
REQUEST_TIMEOUT = 30


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
        }
    )
    return session


def main():
    with make_session() as session:
        response = session.get(CATALOG_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

    rows: list[dict] = []
    seen: set[str] = set()

    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        title = " ".join(link.get_text(" ", strip=True).split())

        if not href.startswith("/catalog/"):
            continue
        if href == "/catalog/":
            continue
        if not title:
            continue
        if href in seen:
            continue

        seen.add(href)

        parts = [part for part in href.strip("/").split("/") if part]
        if not parts or parts[0] != "catalog":
            continue

        slug_parts = parts[1:]
        depth = len(slug_parts)

        rows.append(
            {
                "title": title,
                "href": href,
                "full_url": BASE_URL + href,
                "depth": depth,
                "slug_1": slug_parts[0] if len(slug_parts) > 0 else "",
                "slug_2": slug_parts[1] if len(slug_parts) > 1 else "",
                "slug_3": slug_parts[2] if len(slug_parts) > 2 else "",
                "slug_4": slug_parts[3] if len(slug_parts) > 3 else "",
            }
        )

    df = pd.DataFrame(rows)
    df = df.sort_values(by=["depth", "href", "title"]).reset_index(drop=True)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(OUTPUT_FILE, index=False)

    print("\n=== MAKITA.ONE STRUCTURE ===")
    print(f"Sections collected: {len(df)}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
