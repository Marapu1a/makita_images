# Elitech Catalog PDF Iteration

Source:

- `ELITECH_2025_katalog.pdf` from `elitech.ru`

Input:

- `input/pictures.xlsx`

Outputs:

- `output/import_images/`
- `output/elitech_catalog_pdf_report.xlsx`
- `output/remaining_after_elitech_catalog_pdf.xlsx`

Notes:

- This iteration is an official fallback for articles found in the 2025 PDF catalog.
- Images are extracted by locating the article on a page and cropping the nearest product image.
