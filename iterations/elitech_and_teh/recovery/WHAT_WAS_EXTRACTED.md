# What was extracted / restored for `elitech_and_teh`

## Confirmed extracted artifact

### Honest article slice
- File:
  - `iterations/elitech_and_teh/elitech_and_teh_without_images.xlsx`
- Confirmed content:
  - only products from main sections `Elitech` and `TEH`
  - only rows with empty preview and gallery image fields
  - only rows with non-empty article
- Confirmed volume:
  - `234` rows / `234` unique articles

## Confirmed extraction logic
- Script:
  - `iterations/elitech_and_teh/filter_elitech_and_teh.py`
- Input:
  - `iterations/elitech_and_teh/pictures.xlsx`
- Output:
  - `iterations/elitech_and_teh/elitech_and_teh_without_images.xlsx`

## What was NOT extracted in the restored snapshot
- no product images
- no per-article `import_images/{ARTICLE}/preview.webp`
- no gallery files
- no source reports
- no `remaining_after_*.xlsx`
- no merge report
- no Bitrix import Excel for this block

## Concrete confirmed article trail
The following articles are definitely present in the starting slice and can be used for restart sampling:
- `TPS728-B`
- `204458`
- `205819`
- `205859`
- `205862`
- `215218`
- `215227`
- `215233`
- `204252`
- `204201`
- `210431`
- `205731`
- `214178`
- `186615`
- `198552`
- `TS21509-1`
- `TS22513-2`
- `LPS508-01`
- `205055`
- `191897`

## Practical meaning
The only confirmed extraction already done for this block is the preparation of the clean starting Excel subset.
