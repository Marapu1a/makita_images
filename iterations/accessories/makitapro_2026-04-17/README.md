# makitapro.ru accessories iteration

Input:
- `input/pictures.xlsx`

Output:
- `output/import_images`
- `output/makitapro_report.xlsx`
- `output/remaining_after_makitapro.xlsx`

Workflow:
- search exact article via `/search/index.html?order=tools&term=...`
- keep only exact product links ending with `-i{id}.html`
- on the card, use real `/u/catalog/...large...` and `/u/catalog_item_images/...` files
- ignore `icon.html` thumbnails
- rebuild remainder from actual surviving folders
