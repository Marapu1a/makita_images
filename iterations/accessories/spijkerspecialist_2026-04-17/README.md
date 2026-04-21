# Spijkerspecialist Iteration

Source:
- `https://spijkerspecialist.nl/`

Input:
- `input/pictures.xlsx`

Approach:
- WordPress REST search:
  - `/wp-json/wp/v2/product?search={ARTICLE}&per_page=10`
- strict article filtering on search response and product page
- image extraction from `og:image` and WooCommerce product gallery

Files:
- `download_from_spijkerspecialist.py`
- `build_remaining_after_spijkerspecialist.py`
- `output/import_images`
- `output/spijkerspecialist_report.xlsx`
- `output/remaining_after_spijkerspecialist.xlsx`
