# gama-alati.rs accessories iteration

Input:
- `input/pictures.xlsx`

Output:
- `output/import_images`
- `output/gama_alati_report.xlsx`
- `output/remaining_after_gama_alati.xlsx`

Workflow:
- use `robots.txt` sitemap:
  - `https://www.gama-alati.rs/pub/product_sitemap_1.xml`
- resolve exact product URLs by article from sitemap
- keep only real `/media/catalog/product/` images
- prefer larger cache variants
- rebuild remainder from actual surviving folders
