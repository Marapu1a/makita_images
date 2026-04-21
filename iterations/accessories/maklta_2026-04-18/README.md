Source: `maklta.com.ua`

Input:
- `input/pictures.xlsx`

Working pattern:
- use `sitemap.xml` as the source of exact product URLs
- keep only URLs that contain the article slug
- on the card trust only real images from:
  - `/image/catalog/...`
  - `/userfiles/image/catalog/...`
- keep only image URLs that also contain the article token

Main files:
- `download_from_maklta.py`
- `build_remaining_after_maklta.py`
- `output/maklta_report.xlsx`
- `output/remaining_after_maklta.xlsx`
