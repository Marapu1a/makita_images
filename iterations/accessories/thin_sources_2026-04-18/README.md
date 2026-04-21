# thin_sources

Purpose:
- collect honest singletons and very thin leftovers from previously researched sources
- keep them separate from normal bulk iterations

Current manifest:
- `kirchner24.de`:
  - `643535-4`
- `trgovina-jana.si`:
  - `671326001`
  - `671509001`
  - `671936001`
- `tatmart.com`:
  - `TE00000335`
- `warenhandel.at`:
  - `GB00000132`
- `pitkiskone.fi`:
  - `671002049`
- `maquinaespecialista.cl`:
  - `632H78-9`
- `webmotoculture.com`:
  - `459811-4`
- `karkkainen.com`:
  - `126130-0`
- `gartengeraete-onlineshop.de`:
  - `192075-4`

Important note:
- the three `trgovina-jana.si` articles currently point to the same image URL
- they are still collected intentionally as a thin-source layer for manual review
- `maquinaespecialista.cl` was probed as a possible bulk source, but on the current honest sample only `632H78-9` survived exact-match and non-placeholder checks
- `webmotoculture.com` currently acts as a pure singleton source; exact cards can be clean, but no scalable lookup path is proven yet
- `karkkainen.com` currently acts as a singleton source; card is clean, but no reliable scalable article lookup is proven yet
- `gartengeraete-onlineshop.de` currently acts as a singleton source; direct product card and CDN image are clean, but no scalable lookup path is proven yet

Outputs:
- `output/import_images`
- `output/thin_sources_report.xlsx`
- `output/remaining_after_thin_sources.xlsx`
