# EmmetiStore Iteration

Source:
- `https://www.emmetistore.com/`

Input:
- `input/pictures.xlsx`

Approach:
- do not use on-site search as primary source
- fetch Makita collection JSON from Shopify:
  - `/collections/makita/products.json?limit=250&page=N`
- build a local exact SKU map from `variant.sku`
- download images only for exact article matches

Files:
- `download_from_emmetistore.py`
- `build_remaining_after_emmetistore.py`
- `output/import_images`
- `output/emmetistore_report.xlsx`
- `output/remaining_after_emmetistore.xlsx`

Important:
- honest result after any manual review must be rebuilt from `output/import_images`
- if the user deletes bad folders, rerun `build_remaining_after_emmetistore.py`
