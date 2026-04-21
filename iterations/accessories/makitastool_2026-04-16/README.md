# MakiTasTool Iteration

Source:
- `https://www.makitastool.com/`

Input:
- `input/pictures.xlsx`

Approach:
- WordPress REST search:
  - `/wp-json/wp/v2/product?search={ARTICLE}`
- strict article filtering on search response and product page
- extract product gallery images from WooCommerce HTML

Files:
- `download_from_makitastool.py`
- `build_remaining_after_makitastool.py`
- `output/import_images`
- `output/makitastool_report.xlsx`
- `output/remaining_after_makitastool.xlsx`
