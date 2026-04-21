# Makita Image Collection Pipeline

## What This Project Is

This project is a practical pipeline for filling missing product images in Bitrix exports.

The job was done in two large waves:
- tools
- accessories

The core idea stayed the same in both cases:
- export products from Bitrix to Excel
- keep only rows with empty image columns
- use article number as the main key
- search external sources one by one
- download images into per-article folders
- manually review dirty sources when needed
- rebuild the remaining tail from actual surviving folders, not from optimistic reports
- merge accepted results into a final delivery
- build an Excel file for Bitrix import

## Core Principles

### 1. Article number is the truth

Everything is matched by `Артикул [ARTIKUL]`.

We do not really care whether the product is a tool, accessory, part, battery, bag, or attachment if the article is exact and stable.

### 2. The real truth is folders, not reports

Many source reports were optimistic.
Some sites returned:
- watermarked images
- placeholders
- wrong images on the correct product card
- the same image for many different articles

Because of that, after every manual review we treated this as the only honest state:
- if folder exists
- and it contains `preview.webp`
- then the article is considered covered

Everything else is not covered.

### 3. Manual review is part of the pipeline

This project is intentionally semi-automatic.

Why:
- some sites had anti-bot protection
- some sites had wrong images even on valid product pages
- some sites had source contamination from other shops
- some sites had hidden watermarks

So the correct operating model is:
- automate collection aggressively
- review suspicious sources manually
- rebuild remainder from surviving folders

### 4. Source quality matters more than raw coverage

A source that gives 500 wrong images is worse than a source that gives 20 clean ones.

That is why several apparently strong domains were rejected even after good match counts.

## Legacy Root Scripts

These are the original reusable scripts in the root:
- [filter_makita.py](C:\Users\Valentine\Desktop\makita\py_makita\upload\filter_makita.py)
- [download_imgs.py](C:\Users\Valentine\Desktop\makita\py_makita\upload\download_imgs.py)
- [links_check.py](C:\Users\Valentine\Desktop\makita\py_makita\upload\links_check.py)
- [links_added.py](C:\Users\Valentine\Desktop\makita\py_makita\upload\links_added.py)

Important note:
- [links_added.py](C:\Users\Valentine\Desktop\makita\py_makita\upload\links_added.py) is the old style generator for `pictures_with_links.xlsx`-like files.

## Final Deliveries

### Tools

Final tools delivery:
- [final_delivery_2026-04-09](C:\Users\Valentine\Desktop\makita\py_makita\upload\final_delivery_2026-04-09)

Contains:
- merged `import_images`
- [final_report.xlsx](C:\Users\Valentine\Desktop\makita\py_makita\upload\final_delivery_2026-04-09\final_report.xlsx)
- [pictures_for_import.xlsx](C:\Users\Valentine\Desktop\makita\py_makita\upload\final_delivery_2026-04-09\pictures_for_import.xlsx)
- [pictures_for_bitrix_import.xlsx](C:\Users\Valentine\Desktop\makita\py_makita\upload\final_delivery_2026-04-09\pictures_for_bitrix_import.xlsx)

Tools final logic:
- real images were merged from accepted tool iterations
- unresolved tail was filled with `placeholder.webp`

### Accessories

Final accessories delivery:
- [final_accessories_delivery_2026-04-18](C:\Users\Valentine\Desktop\makita\py_makita\upload\final_accessories_delivery_2026-04-18)

Contains:
- merged `import_images`
- [final_report.xlsx](C:\Users\Valentine\Desktop\makita\py_makita\upload\final_accessories_delivery_2026-04-18\final_report.xlsx)
- [pictures_for_import.xlsx](C:\Users\Valentine\Desktop\makita\py_makita\upload\final_accessories_delivery_2026-04-18\pictures_for_import.xlsx)
- [pictures_for_bitrix_import.xlsx](C:\Users\Valentine\Desktop\makita\py_makita\upload\final_accessories_delivery_2026-04-18\pictures_for_bitrix_import.xlsx)

Final accessory counts:
- baseline unique articles after normalization: `2882`
- real images found: `2603`
- unresolved and covered by placeholder: `279`
- total final folders: `2882`

### Bitrix import path format

Final import Excel files use:
- `/upload/vvm_images/import_images/{FOLDER_NAME}/preview.webp`
- gallery images in the same folder

Important nuance:
- if an article contains filesystem-invalid characters, folder name is sanitized
- example:
  - article: `D-31669/1`
  - folder: `D-31669_1`

Bitrix still matches the row by article column, not by folder name.

## Main Working Flow

### 1. Start from Excel export

For tools:
- export `pictures.xlsx`
- filter products without images

For accessories:
- additionally filter by main section:
  - `Расходные материалы и аксессуары`

Main accessory filter output:
- [accessories_without_images.xlsx](C:\Users\Valentine\Desktop\makita\py_makita\upload\iterations\accessories\accessories_without_images.xlsx)

### 2. Create iteration per source

Rule:
- one source = one dedicated iteration directory

Typical iteration structure:
- `input`
- `output`
- downloader script
- remainder builder
- local `README.md`

This kept the process debuggable and reversible.

### 3. Test source before full run

Never assume a site is useful.

Before full downloader work:
- test a small article sample
- verify exact product match
- verify image is real
- verify no watermark
- verify no placeholders
- verify no repeated generic image across many articles

If source is weak:
- reject it
- or use it only as a thin singleton source

### 4. Download into per-article folders

Expected target structure:
- `import_images/{ARTICLE}/preview.webp`
- optional `gallery_01.webp`, `gallery_02.webp`, etc.

### 5. Manually review suspicious sources

Typical manual actions:
- delete folders with wrong images
- delete watermarked folders
- keep only valid images
- if only one valid image remains, normalize it as `preview.webp`

### 6. Rebuild honest remainder

This step is mandatory after manual review.

Pattern:
- scan `output/import_images`
- keep only folders containing `preview.webp`
- remove those articles from the input Excel
- save a fresh `remaining_after_*.xlsx`

### 7. Merge accepted sources

When enough layers are collected:
- merge accepted iterations by source priority
- keep first valid source per article
- generate final report
- add placeholders for unresolved articles if needed
- generate import Excel

## Source Strategy That Worked

### Bulk sources

These gave meaningful coverage and were worth full iterations.

Accessory wave strong sources included:
- `makitatools.com`
- `makitastool.com`
- `spijkerspecialist.nl`
- `artifex24.de clean`
- `makita-shop.ch`
- `makita-russia.shop`
- `makitapro.ru`

### Thin sources

When the tail became too hard, a new rule was introduced:
- even if a source gives only 1 honest article, still collect it
- do not lose good singletons
- keep them in a dedicated thin-source layer

Thin-source collector:
- [thin_sources_2026-04-18](C:\Users\Valentine\Desktop\makita\py_makita\upload\iterations\accessories\thin_sources_2026-04-18)

This was the right decision.
At the end, wide-source hunting was no longer efficient, but exact singleton recovery still reduced the tail.

## Sources That Looked Good But Were Rejected

These patterns happened often:

### Watermarks

Examples:
- `sparepartsworld.co.uk`
- `makita-pt`
- parts of `makitapro`
- parts of `makita.net.ua`

Rule:
- reject for final use unless manually cleaned

### Wrong images on real product cards

Very important example:
- `makita.one`

Problem:
- article and product title could be correct
- but image on the card could belong to a completely different product

This cannot be solved reliably by pure automation.
It requires visual review.

### Repeated placeholders

Examples:
- generic `image-not-found`
- `machine-onderdeel_*.png`
- `no_img.png`
- one identical image used for many articles

Rule:
- reject source or narrow acceptance rules hard

### Anti-bot / unstable access

Examples:
- `vseinstrumenti.ru`
- some regional or marketplace sites

Rule:
- if source needs repeated manual browser intervention, do not build the pipeline around it

## Anti-patterns Discovered

### Optimistic report is dangerous

A downloader report may say `OK`, but after review the source may become much smaller.

Always rebuild from real folders.

### Search pages pretending to be product matches

Some sites echo the article in:
- query string
- page title
- search text

That creates false positives.

Only trust:
- exact product card
- exact article reference on the card
- real product image

### Marketplace and dealer contamination

Some sites aggregate images from:
- other stores
- distributor feeds
- branded placeholders

The article may still be correct, but image may be watermarked or foreign.

## Files Worth Keeping

Keep:
- final deliveries
- accepted iteration folders
- source tracker
- thin-source collector
- root legacy scripts
- placeholder file
- this `README`
- [PROJECT_CONTEXT.md](C:\Users\Valentine\Desktop\makita\py_makita\upload\PROJECT_CONTEXT.md)

These are the minimum useful memory of the project.

## Files Already Considered Disposable

Safe to remove when they appear again:
- `tmp_inspect*`
- one-off HTML probe dumps
- `__pycache__`
- rejected source iterations with no reusable value
- one-off sample scripts used only for probing

## If This Work Must Be Repeated Later

Recommended restart procedure:

1. Read this file first.
2. Open [PROJECT_CONTEXT.md](C:\Users\Valentine\Desktop\makita\py_makita\upload\PROJECT_CONTEXT.md) for the short current snapshot.
3. For accessories, inspect [SOURCES_TRACKER.md](C:\Users\Valentine\Desktop\makita\py_makita\upload\iterations\accessories\SOURCES_TRACKER.md) before testing new sources.
4. Start from the newest honest remainder file, not from an old optimistic report.
5. When a source is suspicious, prefer manual review early instead of trusting raw download counts.
6. When the tail becomes small and ugly, switch from bulk-source hunting to singleton hunting.
7. Before final delivery, merge everything once, then add placeholders only at the very end.

## Quick Current Snapshot

### Tools

Final ready delivery:
- [final_delivery_2026-04-09](C:\Users\Valentine\Desktop\makita\py_makita\upload\final_delivery_2026-04-09)

### Accessories

Final ready delivery:
- [final_accessories_delivery_2026-04-18](C:\Users\Valentine\Desktop\makita\upload\final_accessories_delivery_2026-04-18)

Accessory result:
- `2882` unique articles in final set
- `2603` with real images
- `279` with placeholder

That is the current practical endpoint of the project.
