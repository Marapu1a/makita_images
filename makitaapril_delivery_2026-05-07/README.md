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
