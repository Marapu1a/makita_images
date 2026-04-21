# makita-russia.shop

Input:
- `input/pictures.xlsx`

Output:
- `output/import_images`
- `output/makita_russia_shop_report.xlsx`
- `output/remaining_after_makita_russia_shop.xlsx`

Workflow:
- build exact article-to-URL candidates from `/sitemap`
- prefer links whose slug ends with the article
- open only the resolved product page
- keep only real `/media/catalog/product/` images
- rebuild remainder from actual surviving folders
