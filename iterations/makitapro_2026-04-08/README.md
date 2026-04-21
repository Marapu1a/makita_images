# MakitaPro Iteration 2026-04-08

Source:

- `https://www.makitapro.ru`

Input:

- `input/pictures.xlsx`

This input was prepared from the previous iteration and already contains only remaining rows with valid articles.

## Notes

- Search form: `GET /search/index.html`
- Search parameters:
  - `order=tools`
  - `term=<article>`
- Product pages use item-style URLs such as:
  - `/Elektricheskij-lobzik-Makita-4329-i167.html`

## Current status

- site is accessible without aggressive anti-bot behavior;
- direct article search works through the site form;
- product pages expose large product images in HTML.
