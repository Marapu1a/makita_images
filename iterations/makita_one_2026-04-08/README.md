# Makita.One Iteration 2026-04-08

Source:

- `https://makita.one`

Input:

- `input/pictures.xlsx`

This input was prepared from the previous iteration and already contains only the remaining rows after `makitapro.ru`.

## Why this source is interesting

- product URLs are clean and stable;
- product pages expose article values in HTML;
- original images are available in `/upload/iblock/...`;
- category tree is visible under `/catalog/...`.

## Important finding

This source does not currently look convenient through direct search by article.

Because of that, the current strategy is:

1. scrape the site category structure;
2. map our Bitrix sections to site sections;
3. try building product URL candidates from section + article;
4. only after that proceed to mass download.
