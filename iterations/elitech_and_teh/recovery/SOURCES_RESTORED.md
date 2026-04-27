# Sources restored for `elitech_and_teh`

Recovery date: 2026-04-27

## Confirmed source inputs inside repo

### Primary input export
- `iterations/elitech_and_teh/pictures.xlsx`
- Role:
  - fresh Bitrix export used as raw input for this block
- Confirmed shape:
  - `61,397` data rows in the first worksheet
  - contains section column `Название основного раздела`
  - contains article column `Артикул [ARTIKUL]`
  - contains image columns:
    - `Картинка для анонса (путь)`
    - `Картинки галереи [MORE_PHOTO]`
- Confirmed section counts relevant to this block inside the raw export:
  - `Elitech`: `2,462`
  - `TEH`: `840`
- This is only the raw export, not the honest working slice.

### Honest starting slice
- `iterations/elitech_and_teh/elitech_and_teh_without_images.xlsx`
- Built by:
  - `iterations/elitech_and_teh/filter_elitech_and_teh.py`
- Role:
  - the real restart point for future source work
- Confirmed shape:
  - `234` data rows
  - `234` non-empty articles
  - `234` unique articles
  - all rows have empty preview and gallery columns
- Confirmed section split:
  - `Elitech`: `224`
  - `TEH`: `10`

## Confirmed filtering rules
From `filter_elitech_and_teh.py`:
- keep only `Название основного раздела` in `{Elitech, TEH}`
- keep only rows where preview image is empty
- keep only rows where gallery images are empty
- keep only rows with non-empty `Артикул [ARTIKUL]`

## Confirmed examples from the starting slice

### TEH examples
- `TPS728-B` — Аккумуляторная батарея для секатора 16V TEH TPS728-B
- `TAP12509-2` — Тарелка опорная для полировальной шлифмашины TEH TAP12509-2
- `TV20L-18` — Фильтр для пылесоса TEH TV20L-18
- `TS21509-1` — Шланг для шлифмашины TEH TS21509-1
- `LPS508-01` — Штанга телескопическая ... TEH LPS508-01

### Elitech examples
- `204458` — Аппарат для сварки полипропиленовых труб
- `205819` — Батарея аккумуляторная
- `215218` — Бита PH1 25мм, 10шт (НАБОР)
- `204252` — Бита PZ1 70мм 1шт
- `210431` — article present in slice, exact source still not searched in restored snapshot

## Sources that were actually checked for this block
Not confirmed in the restored repo snapshot.

Notes:
- `README.md` and `NEXT_STEP.md` say to create one source iteration per source, but do not name any tested source.
- No source-specific scripts or result folders were found under `iterations/elitech_and_teh`.
