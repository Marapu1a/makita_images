# artifex24.de iteration

Input:
- `input/pictures.xlsx`

Main script:
- `download_from_artifex24.py`

Honest remainder builder:
- `build_remaining_after_artifex24.py`

Approach:
- exact article query through `https://www.artifex24.de/?qs={ARTICLE}&search=`
- trust only redirects to a real product page
- validate the article on the final page
- extract product images from `og:image` / product media
