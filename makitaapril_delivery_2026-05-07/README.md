# makitaapril_delivery

Purpose:
- normalize manually collected leftover images from `макитаапрель`
- rebuild them in the same structure as the rest of the project
- prepare Excel files for import

Input:
- source folders: `..\макитаапрель`
- placeholder baseline: `..\placeholder_items_2026-04-27.xlsx`

Output:
- `import_images`
- `final_report.xlsx`
- `pictures_for_import.xlsx`
- `pictures_for_bitrix_import.xlsx`

Rules:
- source folders are matched by placeholder `folder_name`
- original manual files are not modified
- exported files are converted to `webp`
- first image becomes `preview.webp`
- remaining images become `gallery_01.webp`, `gallery_02.webp`, etc.

Verified counts:
- manually found from placeholder list: `291`
- extra manually added article: `CP100DZ`
- `final_report.xlsx` rows: `291`
- `pictures_for_bitrix_import.xlsx` rows: `292`
- import `.webp` files: `347`

Note:
- `import_images` also contains root-level service placeholder files; they are not counted as product images.
