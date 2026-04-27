# Restart plan for `elitech_and_teh`

## Confirmed restart point
Start from:
- `iterations/elitech_and_teh/elitech_and_teh_without_images.xlsx`

Read first:
- `iterations/elitech_and_teh/README.md`
- `iterations/elitech_and_teh/NEXT_STEP.md`
- `README.md`
- `PROJECT_CONTEXT.md`

## What is already known
- this block is prepared as a new image-collection wave
- only the starting slice is confirmed
- no executed source iterations for this block were restored

## Safe replay path

### Step 1. Freeze the baseline
- treat `elitech_and_teh_without_images.xlsx` as baseline `234` rows
- do not replace it
- create new work in dedicated per-source folders under:
  - `iterations/elitech_and_teh/`

Suggested naming pattern:
- `iterations/elitech_and_teh/<source_name>_YYYY-MM-DD/`

### Step 2. Start with a small verification sample
Use a small sample of confirmed articles from the slice, for example:
- `TPS728-B`
- `204458`
- `205819`
- `215218`
- `204252`
- `TS21509-1`
- `LPS508-01`

For every candidate source, confirm manually:
- exact article match on product card
- real image, not placeholder
- no watermark
- no repeated generic image across unrelated articles

### Step 3. Reuse the known Makita workflow
Confirmed generic workflow from project docs:
- one source = one iteration directory
- download into per-article folders
- after manual cleanup, rebuild remainder only from surviving folders with `preview.webp`
- never trust optimistic raw reports

### Step 4. Record every pass immediately
Minimum files to create per source:
- local `README.md`
- downloader script
- output report
- honest `remaining_after_<source>.xlsx`

### Step 5. Keep uncertainty explicit
Mark as `not confirmed` if:
- a source was only sampled, not fully run
- images were downloaded but not manually checked
- a report count differs from surviving folders

## Unknowns that still block a perfect replay
- which external sources were intended first for `Elitech`/`TEH`
- whether any local-only branch or uncommitted work existed outside Git
- whether any downloaded images ever existed for this block outside the repo snapshot

## Current replay difficulty
- rebuilding the same starting point: easy
- replaying an already known successful source path: not possible from current evidence, because such a path was not restored
- starting fresh from the same baseline and same project rules: easy
