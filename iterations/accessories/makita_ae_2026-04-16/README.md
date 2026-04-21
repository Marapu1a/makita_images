# Makita AE Iteration

Source:
- `https://makita.ae/`

Input:
- `input/pictures.xlsx`

Approach:
- `cloudscraper` is required
- site search:
  - `/?s={ARTICLE}&post_type=product`
- strict article filtering on search response and product page
- extract product gallery images from WooCommerce HTML

Files:
- `download_from_makita_ae.py`
- `build_remaining_after_makita_ae.py`
- `output/import_images`
- `output/makita_ae_report.xlsx`
- `output/remaining_after_makita_ae.xlsx`
