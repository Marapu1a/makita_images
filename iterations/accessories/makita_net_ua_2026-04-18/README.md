Source: `makita.net.ua`

Input:
- `input/pictures.xlsx`

Working pattern:
- open search:
  - `https://makita.net.ua/ru/search?search_query={ARTICLE}`
- keep only exact article-coded product links
- on the card trust only the main `og:image` / `ws-store_large` image
- keep the run conservative to avoid noisy related-product images

Main files:
- `download_from_makita_net_ua.py`
- `build_remaining_after_makita_net_ua.py`
- `output/makita_net_ua_report.xlsx`
- `output/remaining_after_makita_net_ua.xlsx`
