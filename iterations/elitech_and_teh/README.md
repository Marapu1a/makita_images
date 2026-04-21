# Elitech And TEH Start Slice

This directory is the starting point for a new image-collection wave.

## Input

- `pictures.xlsx` is the fresh Bitrix export.

## Goal

Build the honest starting slice for further work:

- keep only rows where `Название основного раздела` is `Elitech` or `TEH`
- keep only rows where both image columns are empty:
  - `Картинка для анонса (путь)`
  - `Картинки галереи [MORE_PHOTO]`
- keep only rows with a non-empty `Артикул [ARTIKUL]`

## Output

- `elitech_and_teh_without_images.xlsx`

This file is the starting point for future source iterations.

## Script

- `filter_elitech_and_teh.py`

Run:

```bash
python filter_elitech_and_teh.py
```
