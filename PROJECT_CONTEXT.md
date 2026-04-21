# Project Context

Short current snapshot for quick restart.

For full process details, lessons learned, source strategy, and replay instructions, read:
- [README.md](C:\Users\Valentine\Desktop\makita\py_makita\upload\README.md)

## Current Final Deliveries

### Tools

Ready delivery:
- [final_delivery_2026-04-09](C:\Users\Valentine\Desktop\makita\py_makita\upload\final_delivery_2026-04-09)

Contains:
- merged `import_images`
- final tool report
- Bitrix import Excel

### Accessories

Ready delivery:
- [final_accessories_delivery_2026-04-18](C:\Users\Valentine\Desktop\makita\py_makita\upload\final_accessories_delivery_2026-04-18)

Accessory final counts:
- unique articles after normalization: `2882`
- with real images: `2603`
- with placeholder: `279`
- total final folders: `2882`

Main files:
- [final_report.xlsx](C:\Users\Valentine\Desktop\makita\py_makita\upload\final_accessories_delivery_2026-04-18\final_report.xlsx)
- [pictures_for_import.xlsx](C:\Users\Valentine\Desktop\makita\py_makita\upload\final_accessories_delivery_2026-04-18\pictures_for_import.xlsx)
- [pictures_for_bitrix_import.xlsx](C:\Users\Valentine\Desktop\makita\py_makita\upload\final_accessories_delivery_2026-04-18\pictures_for_bitrix_import.xlsx)

## Current Working Rules

- article number is the main key
- after manual review, the real truth is the contents of `output/import_images`
- use one source per iteration
- keep thin exact one-offs in:
  - [thin_sources_2026-04-18](C:\Users\Valentine\Desktop\makita\py_makita\upload\iterations\accessories\thin_sources_2026-04-18)
- check accessory source history before testing new domains:
  - [SOURCES_TRACKER.md](C:\Users\Valentine\Desktop\makita\py_makita\upload\iterations\accessories\SOURCES_TRACKER.md)

## Key Reusable Scripts

Legacy root scripts:
- [filter_makita.py](C:\Users\Valentine\Desktop\makita\py_makita\upload\filter_makita.py)
- [download_imgs.py](C:\Users\Valentine\Desktop\makita\py_makita\upload\download_imgs.py)
- [links_check.py](C:\Users\Valentine\Desktop\makita\py_makita\upload\links_check.py)
- [links_added.py](C:\Users\Valentine\Desktop\makita\py_makita\upload\links_added.py)

Accessory final builders:
- [build_final_delivery.py](C:\Users\Valentine\Desktop\makita\py_makita\upload\final_accessories_delivery_2026-04-18\build_final_delivery.py)
- [build_import_excel.py](C:\Users\Valentine\Desktop\makita\py_makita\upload\final_accessories_delivery_2026-04-18\build_import_excel.py)

## Important Path Note

If an article contains filesystem-invalid characters, folder name is sanitized for the actual image folder.

Example:
- article: `D-31669/1`
- folder: `D-31669_1`

The import file still matches Bitrix by article column.
  - `output\remaining_after_makita_russia_shop.xlsx`
- honest remainder count: `640`

### 10. makitapro.ru

Iteration folder:
- `iterations\accessories\makitapro_2026-04-17`

Input:
- copied from `makita-russia.shop` honest remainder

Downloader:
- `download_from_makitapro.py`

Working pattern:
- use open search:
  - `https://www.makitapro.ru/search/index.html?order=tools&term={ARTICLE}`
- keep only exact result links ending with `-i{id}.html`
- on product pages use real files from:
  - `/u/catalog/...large...`
  - `/u/catalog_item_images/...`
- ignore `icon.html` thumbnails

Current honest state:
- report `OK`: `262`
- surviving confirmed folders after manual review: `217`
- honest remainder file:
  - `output\remaining_after_makitapro.xlsx`
- honest remainder count: `420`

### 11. gama-alati.rs

Iteration folder:
- `iterations\accessories\gama_alati_2026-04-17`

Input:
- copied from `makitapro` honest remainder

Downloader:
- `download_from_gama_alati.py`

Working pattern:
- use product sitemap from `robots.txt`:
  - `https://www.gama-alati.rs/pub/product_sitemap_1.xml`
- resolve exact product URLs by article from sitemap
- keep only real `/media/catalog/product/` images
- prefer larger cache variants

Current honest state:
- report `OK`: `31`
- surviving confirmed folders after run: `31`
- honest remainder file:
  - `output\remaining_after_gama_alati.xlsx`
- honest remainder count: `389`

### 5. makitastool.com

Iteration folder:
- `iterations\accessories\makitastool_2026-04-16`

Input:
- copied from `emmetistore` honest remainder

Downloader:
- `download_from_makitastool.py`

Working pattern:
- WordPress REST search:
  - `/wp-json/wp/v2/product?search={ARTICLE}`
- strict article filtering in search payload and page HTML
- WooCommerce product gallery extraction

Current honest state:
- surviving confirmed folders so far: `162`
- honest remainder file:
  - `output\remaining_after_makitastool.xlsx`
- honest remainder count: `2,423`

Important nuance:
- the run timed out before finishing the whole input
- the downloader is resumable, and the current result is still useful

### 6. makita.ae

Iteration folder:
- `iterations\accessories\makita_ae_2026-04-16`

Input:
- copied from `makitastool` honest remainder

Downloader:
- `download_from_makita_ae.py`

Working pattern:
- requires `cloudscraper`
- site search:
  - `https://makita.ae/?s={ARTICLE}&post_type=product`
- strict article filtering in search output and page HTML

Current honest state:
- surviving confirmed folders so far: `1`
- honest remainder file:
  - `output\remaining_after_makita_ae.xlsx`
- honest remainder count: `2,422`

Current assessment:
- technically reachable, but too weak to prioritize right now

### 7. spijkerspecialist.nl

Iteration folder:
- `iterations\accessories\spijkerspecialist_2026-04-17`

Input:
- copied from `makitastool` honest remainder

Downloader:
- `download_from_spijkerspecialist.py`

Working pattern:
- WordPress REST search:
  - `/wp-json/wp/v2/product?search={ARTICLE}&per_page=10`
- strict article filtering on search response and product page
- product image extraction from `og:image` and WooCommerce gallery

Current honest state:
- surviving confirmed folders after run: `149`
- honest remainder file:
  - `output\remaining_after_spijkerspecialist.xlsx`
- honest remainder count: `2,274`

Raw report summary for this iteration:
- `OK`: `149`
- `FAIL`: `1,276`
- dominant failure reason: `product_not_found`

### 8. toolnation.es

Iteration folder:
- `iterations\accessories\toolnation_2026-04-17`

Input:
- copied from `spijkerspecialist` honest remainder

Downloader:
- `download_from_toolnation.py`

Working pattern that was tested:
- public product sitemaps:
  - `/sitemap/sitemap_es_1.xml`
  - `/sitemap/sitemap_es_2.xml`
  - `/sitemap/sitemap_es_3.xml`
  - `/sitemap/sitemap_es_4.xml`
- exact article matching against normalized product URLs from the sitemap

Important user validation:
- this source is not usable in production
- although many article URLs exist, the downloaded images turned out to be placeholder/stub images instead of real product photos
- the user manually removed the downloaded output completely

Current honest state:
- do not use this source further
- the working honest input remains:
  - `iterations\accessories\spijkerspecialist_2026-04-17\output\remaining_after_spijkerspecialist.xlsx`
  - honest remainder count: `2,274`

### 9. artifex24.de

Iteration folder:
- `iterations\accessories\artifex24_2026-04-17`

Input:
- copied from `spijkerspecialist` honest remainder

Downloader:
- `download_from_artifex24.py`

Working pattern:
- exact article query through:
  - `https://www.artifex24.de/?qs={ARTICLE}&search=`
- trust only redirects to a real product page
- validate the article in both final URL and page HTML
- extract product images from `og:image` and product media

Current honest state:
- surviving confirmed folders after run: `2,087`
- honest remainder file:
  - `output\remaining_after_artifex24.xlsx`
- honest remainder count: `180`

Raw report summary for this iteration:
- `OK`: `2,087`
- `FAIL`: `179`
- dominant failure reason: `article_not_in_final_url`

### 10. artifex24.de clean

Iteration folder:
- `iterations\accessories\artifex24_clean_2026-04-17`

Input:
- copied from `spijkerspecialist` honest remainder

Downloader:
- `download_from_artifex24.py`

What was tightened:
- search pages are no longer accepted as product pages
- exact product links can be extracted from the search result page when they exist
- image URLs must match the article itself, not just the page text
- image size variants are collapsed
- repeated preview hashes are tracked and audited

Current honest state:
- surviving confirmed folders after clean run: `896`
- honest remainder file:
  - `output\remaining_after_artifex24.xlsx`
- honest remainder count: `1,373`

Audit helper:
- duplicate hash report:
  - `output\duplicate_hashes.xlsx`

Current practical note:
- this clean run is much less noisy than the original `artifex24` pass
- top repeated hashes dropped sharply; the largest cluster is now `22`, not `200+`
- the remaining duplicate groups are mostly clustered within close article series and may be partially legitimate

### 11. intermediate accessories delivery

Delivery folder:
- `iterations\accessories\intermediate_delivery_2026-04-17`

What it contains:
- merged `import_images` from all accepted accessory iterations
- `intermediate_report.xlsx` with chosen source per article
- `intermediate_conflicts.xlsx` for overlaps between accepted iterations
- `remaining_after_intermediate.xlsx` built from the full accessory input

Merge result:
- chosen articles in one place: `1,515`
- conflicts across accepted sources: `27`
- honest remaining accessory rows: `1,370`

Source priority used for the merge:
- `makitatools.com`
- `makitasparesm.com`
- `emmetistore.com`
- `makitastool.com`
- `spijkerspecialist.nl`
- `makita.ae`
- `artifex24.de clean`

Cleanup performed:
- removed rejected `sparepartsworld` iteration after merge
- removed older dirty `artifex24` iteration after merge
- removed rejected `makita-pt` iteration after watermark check

### 12. makita-shop.ch

Iteration folder:
- `iterations\accessories\makita_shop_ch_2026-04-17`

Input:
- copied from `intermediate_delivery` honest remainder

Downloader:
- `download_from_makita_shop_ch.py`

Working pattern:
- direct article detail URL:
  - `https://makita-shop.ch/detail/{ARTICLE}`
- accept only real detail pages
- accept only real product images from:
  - `stagente.sirv.com/makita/`
- reject placeholders and generic site media

Current honest state:
- surviving confirmed folders after run: `163`
- honest remainder file:
  - `output\remaining_after_makita_shop_ch.xlsx`
- honest remainder count: `1,207`

Raw report summary for this iteration:
- `OK`: `163`
- `FAIL`: `1,204`
- dominant failure reasons:
  - `detail_not_found`
  - `no_real_image`

## Source Tracking

A dedicated accessories source registry now exists:
- `c:\Users\Valentine\Desktop\makita\py_makita\upload\iterations\accessories\SOURCES_TRACKER.md`

Current queued next candidates from that tracker:
- current honest accessories tail:
  - `c:\Users\Valentine\Desktop\makita\py_makita\upload\iterations\accessories\thin_sources_2026-04-18\output\remaining_after_thin_sources.xlsx`
  - rows remaining: `279`
- latest completed source:
  - `thin_sources`
  - input `290`
  - confirmed folders `11` after manual review
  - honest remainder `279`
- recent weak / rejected research:
  - `in-te.cz` has some exact matches, but too many default thumbnails
  - `wmv-dresden.de` exposes exact article URLs, but product pages fall back to `kein.png`
  - `cjsinclairltd.co.uk` finds exact products, but sampled images look like repeated generic screenshots
  - `pitkiskone.fi` search is too noisy and creates broad false positives
  - `gtxservice.com` has real cards but almost no exact coverage on the current honest tail
  - `reposicaoonline.com.br` remains only a niche fallback
  - `makitatrading.ru` remains deferred because the site is extremely slow
  - `elektroserw.com.pl` gives exact product links, but cards fall back to the same generic `makita-miniaturka.jpg`
  - `leitermann.de` has public product pages, but current-tail coverage is near zero and media is noisy
  - `makita.sklep.pl` has watermarked images
  - `makita-ua.com.ua` is clean but very thin on the current tail
  - `makitauae.com` remains only a niche fallback after a fresh sitemap-based check
  - `maklta.com.ua` turned out to be narrow but valid; it has already been exhausted as a completed layer
  - `szerszamkell.hu` has isolated clean direct cards, but the current honest tail gives `0/306` via sitemap and the internal search is false-positive noise
  - `robeks.si` has isolated clean direct cards, but only `0/15` on a local honest sample
  - `zip4tools.ru` returns practically empty HTML in shell requests, so there is no trustworthy automation path
  - `ersatzteil-service.de` exposes exact part pages, but sampled media falls back to `kein.jpg`
  - `vmshop.cz` stays only under investigation for now: one clean exact card is confirmed, but sample coverage is still too weak for a full run
  - `mtools.be` is partially usable only with a very strict filter: many cards point to repeated generic `makita_onderdelen_*.jpg`, but article-coded media filenames produce a small clean layer
  - `tatmart.com` has real cards, but only about `3/100` on the current tail sample
  - `ultimamac.com` has real pages, but current-tail coverage is `0` and the media leans on logo/drawing imagery
  - `kirchner24.de` has clean exact cards, but only one current-tail sitemap hit
  - `tkoutils.fr` is too dirty for bulk use because several different exact URLs collapse onto repeated placeholder hashes
  - `elektroservis-povse.com` has real cards, but the local search is a false-positive wall and no clean lookup path is proven
  - `trgovina-jana.si` has sitemap and clean exact cards, but only `4/100` on the current tail
  - thin singletons are now collected in a dedicated layer instead of being ignored between bulk iterations

Latest promising discovery:
- `makita.net.ua`
  - open search:
    - `https://makita.net.ua/ru/search?search_query={ARTICLE}`
    - `https://makita.net.ua/uk/search?search_query={ARTICLE}`
  - open sitemap index:
    - `https://makita.net.ua/1_index_sitemap.xml`
  - exact sample result on the current honest tail:
    - `27/60`
  - sampled product pages have real article-coded links and real product images
  - full run already completed:
    - `62` confirmed folders after manual review
    - `327` rows remain
  - manual review found that some product cards reused third-party watermarked images, so the source is only partially clean and the remainder must always be rebuilt from actual surviving folders

## How To Continue From A New Dialog

1. Read this file first.
2. For accessories, start from:
- `c:\Users\Valentine\Desktop\makita\py_makita\upload\iterations\accessories\thin_sources_2026-04-18\output\remaining_after_thin_sources.xlsx`
3. When testing a new source:
- first verify it really covers the remaining articles
- do not trust the source just because the site is large
- prefer sources with article-based search or direct product pages
4. After every download pass:
- inspect `output\import_images`
- if the user manually deletes bad folders, rebuild the remainder from folder names
5. If the context window gets tight again:
- update this file with the newest counts, source result, and next starting file

## Working Style Agreed With The User

- create a new directory for each meaningful iteration/source
- do not create unnecessary clutter
- delete clearly temporary throwaway files when safe
- prefer truthful remainders from actual folder contents after manual review
- if a source gives even partial value, it can still be worth exhausting
- keep communication in Russian
