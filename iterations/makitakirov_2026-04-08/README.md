# Makita Kirov Iteration 2026-04-08

This iteration targets `https://макитакиров.рф/`.

Technical host:

- `https://xn--80aagwbjclyts.xn--p1ai/`

## Workflow

1. Input export is stored in `input/pictures.xlsx`.
2. Run `filter_makitakirov.py`.
3. Review `work/tools_without_images.xlsx`.
4. Run `build_makitakirov_candidates.py`.
5. Use `work/makitakirov_candidates.xlsx` for matching and download.

## Source check

Checked on April 8, 2026:

- the site resolves in DNS;
- direct HTTP requests return `200`;
- search works via `/search?q=...`;
- no hard anti-bot behavior was seen during initial probing.
