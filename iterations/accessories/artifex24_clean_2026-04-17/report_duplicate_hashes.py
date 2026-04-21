from __future__ import annotations

from collections import defaultdict
import hashlib
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
IMAGES_DIR = BASE_DIR / "output" / "import_images"
OUTPUT_FILE = BASE_DIR / "output" / "duplicate_hashes.xlsx"


def main() -> None:
    groups: dict[str, list[str]] = defaultdict(list)
    for folder in IMAGES_DIR.iterdir():
        preview = folder / "preview.webp"
        if not folder.is_dir() or not preview.exists():
            continue
        file_hash = hashlib.md5(preview.read_bytes()).hexdigest()
        groups[file_hash].append(folder.name)

    rows: list[dict] = []
    for file_hash, articles in sorted(groups.items(), key=lambda item: len(item[1]), reverse=True):
        if len(articles) < 2:
            continue
        rows.append(
            {
                "hash": file_hash,
                "count": len(articles),
                "articles": ", ".join(sorted(articles)),
            }
        )

    pd.DataFrame(rows).to_excel(OUTPUT_FILE, index=False)
    print(f"duplicate groups: {len(rows)}")
    print(f"saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
