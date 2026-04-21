from __future__ import annotations

from pathlib import Path
import re
import shutil

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT_DIR / "iterations" / "accessories"
FINAL_DIR = Path(__file__).resolve().parent
FINAL_IMAGES_DIR = FINAL_DIR / "import_images"
FINAL_REPORT_FILE = FINAL_DIR / "final_report.xlsx"
README_FILE = FINAL_DIR / "README.md"
PLACEHOLDER_FILE = ROOT_DIR / "placeholder.webp"

BASELINE_FILE = BASE_DIR / "accessories_without_images.xlsx"

COL_ARTICLE = "Артикул [ARTIKUL]"
COL_NAME = "Наименование элемента"

SOURCES = [
    {
        "iteration": "makitatools_2026-04-16",
        "site": "makitatools.com",
        "images_dir": BASE_DIR / "makitatools_2026-04-16" / "output" / "import_images",
    },
    {
        "iteration": "makitasparesm_2026-04-16",
        "site": "makitasparesm.com",
        "images_dir": BASE_DIR / "makitasparesm_2026-04-16" / "output" / "import_images",
    },
    {
        "iteration": "emmetistore_2026-04-16",
        "site": "emmetistore.com",
        "images_dir": BASE_DIR / "emmetistore_2026-04-16" / "output" / "import_images",
    },
    {
        "iteration": "makitastool_2026-04-16",
        "site": "makitastool.com",
        "images_dir": BASE_DIR / "makitastool_2026-04-16" / "output" / "import_images",
    },
    {
        "iteration": "spijkerspecialist_2026-04-17",
        "site": "spijkerspecialist.nl",
        "images_dir": BASE_DIR / "spijkerspecialist_2026-04-17" / "output" / "import_images",
    },
    {
        "iteration": "makita_ae_2026-04-16",
        "site": "makita.ae",
        "images_dir": BASE_DIR / "makita_ae_2026-04-16" / "output" / "import_images",
    },
    {
        "iteration": "artifex24_clean_2026-04-17",
        "site": "artifex24.de clean",
        "images_dir": BASE_DIR / "artifex24_clean_2026-04-17" / "output" / "import_images",
    },
    {
        "iteration": "makita_shop_ch_2026-04-17",
        "site": "makita-shop.ch",
        "images_dir": BASE_DIR / "makita_shop_ch_2026-04-17" / "output" / "import_images",
    },
    {
        "iteration": "makita_russia_shop_2026-04-17",
        "site": "makita-russia.shop",
        "images_dir": BASE_DIR / "makita_russia_shop_2026-04-17" / "output" / "import_images",
    },
    {
        "iteration": "makitapro_2026-04-17",
        "site": "makitapro.ru",
        "images_dir": BASE_DIR / "makitapro_2026-04-17" / "output" / "import_images",
    },
    {
        "iteration": "gama_alati_2026-04-17",
        "site": "gama-alati.rs",
        "images_dir": BASE_DIR / "gama_alati_2026-04-17" / "output" / "import_images",
    },
    {
        "iteration": "makita_net_ua_2026-04-18",
        "site": "makita.net.ua",
        "images_dir": BASE_DIR / "makita_net_ua_2026-04-18" / "output" / "import_images",
    },
    {
        "iteration": "maklta_2026-04-18",
        "site": "maklta.com.ua",
        "images_dir": BASE_DIR / "maklta_2026-04-18" / "output" / "import_images",
    },
    {
        "iteration": "mtools_be_2026-04-18",
        "site": "mtools.be",
        "images_dir": BASE_DIR / "mtools_be_2026-04-18" / "output" / "import_images",
    },
    {
        "iteration": "thin_sources_2026-04-18",
        "site": "thin_sources",
        "images_dir": BASE_DIR / "thin_sources_2026-04-18" / "output" / "import_images",
    },
]


def normalize_article(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().upper()
    return re.sub(r"\s+", "", text)


def safe_folder_name(article: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", article)


def folder_has_preview(folder: Path) -> bool:
    return folder.is_dir() and (folder / "preview.webp").exists()


def copy_real_folder(source_dir: Path, target_dir: Path) -> int:
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir)
    return len(list(target_dir.glob("*.webp")))


def create_placeholder_folder(target_dir: Path) -> int:
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PLACEHOLDER_FILE, target_dir / "preview.webp")
    return 1


def load_baseline() -> pd.DataFrame:
    df = pd.read_excel(BASELINE_FILE)
    df["_article_norm"] = df[COL_ARTICLE].map(normalize_article)
    df = df[df["_article_norm"] != ""].copy()
    df = df.drop_duplicates(subset=["_article_norm"]).reset_index(drop=True)
    return df


def collect_source_articles() -> dict[str, dict[str, Path]]:
    source_articles: dict[str, dict[str, Path]] = {}
    for source in SOURCES:
        articles: dict[str, Path] = {}
        source_dir = source["images_dir"]
        if source_dir.exists():
            for folder in source_dir.iterdir():
                if folder_has_preview(folder):
                    articles[normalize_article(folder.name)] = folder
        source_articles[source["iteration"]] = articles
    return source_articles


def main() -> None:
    if not PLACEHOLDER_FILE.exists():
        raise FileNotFoundError(f"Placeholder file not found: {PLACEHOLDER_FILE}")

    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    if FINAL_IMAGES_DIR.exists():
        shutil.rmtree(FINAL_IMAGES_DIR)
    FINAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    baseline_df = load_baseline()
    names = {
        normalize_article(row.get(COL_ARTICLE, "")): str(row.get(COL_NAME, "")).strip()
        for _, row in baseline_df.iterrows()
    }

    source_articles = collect_source_articles()
    article_sources: dict[str, list[dict[str, str]]] = {}
    for source in SOURCES:
        iteration = source["iteration"]
        for article in source_articles[iteration]:
            article_sources.setdefault(article, []).append(
                {
                    "iteration": iteration,
                    "site": source["site"],
                }
            )

    rows: list[dict] = []
    chosen_articles: set[str] = set()
    conflict_count = 0
    placeholder_count = 0

    for _, row in baseline_df.iterrows():
        article = normalize_article(row.get(COL_ARTICLE, ""))
        if not article:
            continue

        candidates = article_sources.get(article, [])
        folder_name = safe_folder_name(article)
        target_dir = FINAL_IMAGES_DIR / folder_name

        if candidates:
            chosen = candidates[0]
            source_dir = next(item["images_dir"] for item in SOURCES if item["iteration"] == chosen["iteration"])
            copied_files = copy_real_folder(source_dir / article, target_dir)
            chosen_articles.add(article)

            if len(candidates) > 1:
                conflict_count += 1

            rows.append(
                {
                    "article": article,
                    "name": names.get(article, ""),
                    "final_status": "REAL_IMAGE",
                    "final_iteration": chosen["iteration"],
                    "final_site": chosen["site"],
                    "source_count": len(candidates),
                    "all_sources": ", ".join(item["site"] for item in candidates),
                    "images_copied": copied_files,
                    "folder_name": folder_name,
                    "folder": f"import_images/{folder_name}",
                    "placeholder_used": "NO",
                }
            )
        else:
            copied_files = create_placeholder_folder(target_dir)
            placeholder_count += 1
            rows.append(
                {
                    "article": article,
                    "name": names.get(article, ""),
                    "final_status": "PLACEHOLDER",
                    "final_iteration": "placeholder",
                    "final_site": "placeholder",
                    "source_count": 0,
                    "all_sources": "",
                    "images_copied": copied_files,
                    "folder_name": folder_name,
                    "folder": f"import_images/{folder_name}",
                    "placeholder_used": "YES",
                }
            )

    remaining = baseline_df[~baseline_df["_article_norm"].isin(chosen_articles)].copy()
    report_df = pd.DataFrame(rows).sort_values(by=["placeholder_used", "article"], ascending=[True, True]).reset_index(drop=True)
    report_df.to_excel(FINAL_REPORT_FILE, index=False)

    README_FILE.write_text(
        "\n".join(
            [
                "# Final Accessories Delivery",
                "",
                "Contents:",
                "- `import_images` - merged folders for all accessory articles from the baseline",
                "- `final_report.xlsx` - chosen source or placeholder status for every article",
                "",
                "Important:",
                "- placeholders are used for unresolved articles",
                "- every baseline article gets its own folder with `preview.webp`",
                f"- baseline rows with article: {len(baseline_df)}",
                f"- merged real articles: {len(chosen_articles)}",
                f"- placeholder articles: {placeholder_count}",
                f"- unresolved articles covered by placeholder: {len(remaining)}",
                f"- conflicts resolved by source priority: {conflict_count}",
                "",
                "Source priority:",
                *[f"- `{source['site']}` ({source['iteration']})" for source in SOURCES],
            ]
        ),
        encoding="utf-8",
    )

    print("\n=== FINAL ACCESSORIES DELIVERY SUMMARY ===")
    print(f"Baseline rows with article: {len(baseline_df)}")
    print(f"Merged real articles: {len(chosen_articles)}")
    print(f"Placeholder articles: {placeholder_count}")
    print(f"Unresolved rows covered by placeholder: {len(remaining)}")
    print(f"Conflicts resolved by priority: {conflict_count}")
    print(f"Final images dir: {FINAL_IMAGES_DIR}")
    print(f"Final report: {FINAL_REPORT_FILE}")


if __name__ == "__main__":
    main()
