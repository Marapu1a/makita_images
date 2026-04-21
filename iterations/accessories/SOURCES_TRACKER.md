# Accessories Sources Tracker

Current honest input:
- `iterations/accessories/thin_sources_2026-04-18/output/remaining_after_thin_sources.xlsx`
- rows remaining: `279`

Rules:
- always check this file before testing new domains
- do not re-test sources that are already exhausted unless a new technical path appears
- after any manual review, rebuild remainder from actual `output/import_images`

## Completed Iterations

| Source | Status | Result | Notes |
| --- | --- | --- | --- |
| `makitatools.com` | completed | `195` confirmed after manual review | direct product pages by article |
| `makitasparesm.com` | completed | `42` confirmed after manual review | WooCommerce search, strong noise after manual filtering |
| `emmetistore.com` | completed | `68` confirmed | Shopify collection JSON, exact `variant.sku` matching |
| `makitastool.com` | in progress | `162` confirmed so far | timed out mid-run, resumable |
| `spijkerspecialist.nl` | completed | `149` confirmed | clean product images, WordPress REST search |
| `artifex24.de` | completed | `2087` confirmed | direct search redirect `/?qs={ARTICLE}&search=` with exact article validation |
| `artifex24.de clean` | completed | `896` confirmed | stricter product-page validation, image filtering, duplicate audit |
| `makita-shop.ch` | completed | `163` confirmed | direct detail pages with strict real-image filtering |
| `makita-russia.shop` | completed | `567` confirmed | sitemap-based exact article linking, clean product media |
| `makitapro.ru` | completed | `217` confirmed after manual review | exact search matches, real `large` and `catalog_item_images` files |
| `gama-alati.rs` | completed | `31` confirmed | exact article matches from product sitemap, clean catalog product media |
| `makita.net.ua` | completed | `62` confirmed after manual review | open Prestashop search, exact article-coded product links, some cards had third-party watermarked images and were removed manually |
| `maklta.com.ua` | completed | `22` confirmed after manual review | sitemap-based exact URL matching, mostly clean catalog image paths; one watermarked folder removed manually |
| `mtools.be` | completed | `16` confirmed | sitemap-based exact URL matching with hard media filter: trust only image filenames that contain the same article token |
| `thin_sources` | completed | `11` confirmed after manual review | separate micro-layer for honest singletons and very thin sources |

## Checked And Rejected

| Source | Status | Notes |
| --- | --- | --- |
| `makita.com.mx` | rejected | weak accessory coverage |
| `makita-pt.ru` | rejected for use | search and cards work, but product images contain watermarks |
| `sparepartsworld.co.uk` | rejected for use | strong coverage, but images have watermarks and cannot be used; iteration removed after intermediate merge |
| `toolnation.es` | rejected for use | many exact article matches, but downloaded images were placeholder/stub images instead of real product photos |
| `makita.ae` | low value | technically works with `cloudscraper`, but current run gave only `1` confirmed folder |
| `toolmax.nl` | blocked | still returns `403`, even with browser-like client |
| `mima.de` | blocked | returns protection page / `403` on direct requests |
| `makita-land.ru` | rejected for use | this is the target site we are filling ourselves, so it cannot be a source |
| `makitatrading.ru` | deferred | real product pages and sitemap exist, but the site is extremely slow; no clean scalable article-to-card path found yet |
| `powertoolreplacementparts.com` | rejected for use | direct pages are accessible, but sampled product media resolves to generic brand/logo imagery instead of reliable part photos |
| `sleequipment.com` | rejected for use | direct pages are accessible, but sampled product media is generic Makita brand imagery rather than trustworthy part photos |
| `strument.com.ua` | blocked | Cloudflare challenge on search pages |
| `klium.com` | blocked | Cloudflare challenge on search pages |
| `encompass.com` | blocked | Cloudflare challenge on direct product pages |
| `reposicaoonline.com.br` | low value | real search and real part photos, but only `1/20` on current tail sample |
| `in-te.cz` | rejected for use | exact URLs exist for a subset, but many matched cards use default thumbnail / generic preview instead of trustworthy product photo |
| `wmv-dresden.de` | rejected for use | sitemap exposes exact article URLs, but product pages fall back to `kein.png` / no-photo style placeholders |
| `cjsinclairltd.co.uk` | rejected for use | Shopify search finds exact products, but sampled images look like repeated generic screenshots rather than reliable part photos |
| `pitkiskone.fi` | rejected for use | search is noisy and returns broad mower pages; article text alone creates massive false positives |
| `gtxservice.com` | low value | direct cards and images are real, but current tail sample gives almost no exact article hits |
| `elektroserw.com.pl` | rejected for use | exact product links exist, but sampled cards all fall back to the same generic `makita-miniaturka.jpg` image |
| `leitermann.de` | rejected for use | exact web hits exist for some Makita accessories, but local coverage on the current tail is near-zero and product/media pages are too noisy |
| `makita.sklep.pl` | rejected for use | exact accessory cards exist, but sampled `og:image` files are watermarked |
| `makita-ua.com.ua` | low value | clean cards and images exist, but only `2/40` exact useful hits on the current tail |
| `szerszamkell.hu` | rejected for use | clean direct cards exist for isolated parts, but on the current honest tail the sitemap gives `0/306` and internal search is effectively false-positive noise |
| `robeks.si` | low value | isolated clean direct cards exist, but local search gives `0/15` on the current honest sample |
| `zip4tools.ru` | rejected for use | pages are practically empty in shell requests; no stable searchable HTML or trustworthy media path found |
| `ersatzteil-service.de` | rejected for use | exact article pages exist for some parts, but sampled media falls back to `/bilder/artikelbilder/kein.jpg` |
| `vmshop.cz` | under investigation | sitemap is open and at least one exact clean card exists (`632C23-4`), but current-tail sample coverage is still too weak to justify a full run |
| `tatmart.com` | low value | real cards and real images exist, but only about `3/100` on the current tail sample |
| `ultimamac.com` | rejected for use | real pages exist, but current-tail sitemap coverage is `0`, and cards lean on generic logo/drawing media |
| `kirchner24.de` | low value | exact clean cards exist, but current-tail sitemap gives only `1` match (`643535-4`) |
| `tkoutils.fr` | rejected for use | many exact URLs exist, but image hashes show repeated placeholders and generic repeated media |
| `elektroservis-povse.com` | rejected for use | exact cards exist, but local search is a noisy false-positive wall and no clean scalable lookup path is proven |
| `trgovina-jana.si` | low value | sitemap and clean exact cards exist, but current-tail coverage is only `4/100` |
| `agrigardenstore.com` | low value | exact clean cards exist, but no sitemap path was recovered and current-tail scalable lookup is still missing |
| `agrodirect.at` | low value | exact clean cards exist, but no sitemap/search path was recovered and coverage looks very thin |
| `maquinaespecialista.cl` | low value | open search works and exact clean cards exist, but on the current honest sample only `632H78-9` survived non-placeholder checks |
| `webmotoculture.com` | low value | exact clean cards exist for isolated mower parts, but no scalable lookup path is proven yet |
| `karkkainen.com` | low value | clean exact singleton card exists, but no reliable scalable article lookup is proven yet |
| `gartengeraete-onlineshop.de` | low value | clean exact singleton card exists with CDN image, but no scalable article lookup is proven yet |

## Current Queue

| Priority | Source | Check Result | Technical Path | Next Action |
| --- | --- | --- | --- | --- |
| `1` | `line-tools.ru` | `1/5` on a quick small sample | site search `search/?q={ARTICLE}` | low priority fallback only |
| `2` | `makitastool.com` | current run already produced `162` folders | WordPress REST search `wp-json/wp/v2/product?search={ARTICLE}` | return only if a new bypass for `403` appears |
| `3` | `verktoy.no` | weak on current tail | Magento product cards but no good article lookup path found yet | low priority unless a new sitemap/article strategy appears |
| `4` | `reposicaoonline.com.br` | low but real hits on exact part numbers | local search `/procura?procura={ARTICLE}` | niche fallback only |
| `5` | `makitauae.com` | direct `/product/{ARTICLE}/` works only for a tiny subset | exact article page pattern | niche fallback only |
| `6` | `makita.net.ua` | completed | Prestashop search `/ru/search?search_query={ARTICLE}` with exact article-coded product links | already exhausted on current tail slice |
| `7` | `makitauae.com` | `3/60` on current honest tail via product sitemaps | Yoast `product-sitemap*.xml` + direct `/product/{ARTICLE}/` pages | niche fallback only |
| `8` | `vmshop.cz` | one proven clean exact card, weak current sample | sitemap index + exact article-coded product pages | revisit only if another article-to-URL strategy appears |
| `9` | `makitatrading.ru` | still technically promising, still operationally slow | sitemap + very heavy Bitrix search pages | retry only with a cleaner search-to-card extraction path |

## Notes By Source

### `sparepartsworld.co.uk`
- exact article URLs are live for many accessories
- product image is embedded directly in HTML via:
  - `/images_spares/sparepartsworld/...jpg`
- iteration result:
  - input `2585`
  - confirmed folders `157`
  - honest remainder `2428`
- rejected for production use because the images carry watermarks

### `makitastool.com`
- search pages are noisy
- WordPress REST endpoint works:
  - `/wp-json/wp/v2/product?search={ARTICLE}`
- requires exact article filtering in JSON payload before trusting hits
- current partial iteration result:
  - input `2585`
  - confirmed folders `162`
  - honest remainder `2423`
- run timed out, but the downloader is resumable and already useful

### `makita.ae`
- plain requests hit ModSecurity
- `cloudscraper` works
- site search can be used with:
  - `https://makita.ae/?s={ARTICLE}&post_type=product`
- current run result:
  - input `2423`
  - confirmed folders `1`
  - honest remainder `2422`
- currently too weak to prioritize further

### `spijkerspecialist.nl`
- web search already shows exact accessory product pages
- examples found:
  - `134890-0`
  - `JM23100117`
- also exposes category pages with many Makita accessories
- current iteration result:
  - input `2423`
  - confirmed folders `149`
  - honest remainder `2274`
- clean images, no watermark issue detected on sampled output

### `artifex24.de`
- exact article query redirects to a real product page:
  - `https://www.artifex24.de/?qs={ARTICLE}&search=`
- use only exact redirects where the article is present in both final URL and page HTML
- product image comes from the page itself (`og:image` / product media), no watermark issue detected on sampled output
- current iteration result:
  - input `2274`
  - confirmed folders `2087`
  - honest remainder `180`

### `artifex24.de clean`
- separate clean rerun created to avoid mixing dirty and clean results
- stricter rules:
  - accept only real product URLs, not raw search pages
  - allow exact result links from search output when present
  - keep only image URLs tied to the article itself
  - collapse image size variants
  - flag excessive repeated preview hashes
- current clean iteration result:
  - input `2274`
  - confirmed folders `896`
  - honest remainder `1373`
- duplicate audit file:
  - `iterations/accessories/artifex24_clean_2026-04-17/output/duplicate_hashes.xlsx`

### `intermediate delivery`
- merged accepted folders from valid iterations into one working delivery:
  - `iterations/accessories/intermediate_delivery_2026-04-17`
- chosen articles: `1515`
- conflict articles across valid sources: `27`
- honest remainder from full accessories input: `1370`
- main files:
  - `intermediate_report.xlsx`
  - `intermediate_conflicts.xlsx`
  - `remaining_after_intermediate.xlsx`

### `makitasale.ru`
- local search is open:
  - `https://makitasale.ru/catalog/?q={ARTICLE}`
- sample before `artifex24`: `23/40`
- exact product links are visible in search results for matched articles

### `makita-shop.ch`
- direct article detail URLs can work:
  - `https://makita-shop.ch/detail/{ARTICLE}`
- clean iteration result:
  - input `1370`
  - confirmed folders `163`
  - honest remainder `1207`
- use only exact detail pages and only real product images from `stagente.sirv.com/makita/`
- placeholders and generic site media are rejected

### `makita-russia.shop`
- sitemap is publicly accessible:
  - `https://makita-russia.shop/sitemap`
- working approach:
  - build exact article-to-URL candidates from sitemap anchors
  - prefer links whose slug ends with the article
  - open only the resolved product page
  - keep only real `/media/catalog/product/` images
- current iteration result:
  - input `1207`
  - confirmed folders `567`
  - honest remainder `640`

### `makitapro.ru`
- search is open:
  - `https://www.makitapro.ru/search/index.html?order=tools&term={ARTICLE}`
- working approach:
  - keep only exact search hits ending with `-i{id}.html`
  - on the card use real image files from:
    - `/u/catalog/...large...`
    - `/u/catalog_item_images/...`
  - ignore `icon.html` thumbnails
- current iteration result:
  - input `640`
  - report `OK`: `262`
  - honest confirmed folders after manual review: `217`
  - honest remainder: `420`

### `gama-alati.rs`
- hidden sitemap is listed in `robots.txt`:
  - `https://www.gama-alati.rs/pub/product_sitemap_1.xml`
- working approach:
  - resolve exact product URLs by article from sitemap
  - keep only real `/media/catalog/product/` images
  - prefer larger cache variants
- current iteration result:
  - input `420`
  - report `OK`: `31`
  - honest confirmed folders: `31`
  - honest remainder: `389`

### `makitatrading.ru`
- direct product pages are real and accessible, example:
  - `https://makitatrading.ru/catalog/product/112120/`
- `sitemap-iblock-3.xml` is publicly reachable, but very slow and large
- search pages do not expose an easy exact-match path from the current shell workflow
- partial streamed product HTML contains the article early, but product media does not appear early enough to make a clean fast parser practical
- keep as a possible later fallback only if a better article-to-URL strategy appears

### `reposicaoonline.com.br`
- open search works:
  - `https://www.reposicaoonline.com.br/procura?procura={ARTICLE}`
- direct product pages have real part images under:
  - `/public/reposicaoonline/imagens/produtos/`
- current tail sample result:
  - `1/20` exact useful hits
- too thin for a full iteration right now, but viable as a niche fallback for individual leftovers

### `in-te.cz`
- large sitemap is open:
  - `https://www.in-te.cz/sitemap.xml`
- current honest tail sample result:
  - `18/60` rough sitemap hits
- problem:
  - a meaningful share of matched cards falls back to:
    - `/data/temp/product-images/default-thumbnail-product-preview.jpg`
  - so coverage signal is real, but image quality is too unreliable for a clean bulk run

### `wmv-dresden.de`
- article sitemap is open:
  - `https://shop.wmv-dresden.de/wmv-dresden-artikel/sitemap.xml`
- exact article URLs do exist, example:
  - `https://shop.wmv-dresden.de/artikeldetails/671002049DOL`
- current honest tail sample result:
  - only `3/60` via sitemap
- problem:
  - sampled product pages expose `kein.png` / no-photo style placeholders instead of trustworthy product media

### `cjsinclairltd.co.uk`
- Shopify search works:
  - `https://www.cjsinclairltd.co.uk/search?q={ARTICLE}&type=product`
- current honest tail sample result:
  - `8/60`
- problem:
  - sampled product images are repeated screenshot-like PNG files and do not look reliable enough for production import

### `pitkiskone.fi`
- sitemap is open:
  - `https://pitkiskone.fi/sitemap.xml`
- search endpoint is open:
  - `https://pitkiskone.fi/haku?q={ARTICLE}`
- problem:
  - article string appears on broad result pages and creates huge false positives
  - sampled hits collapsed onto unrelated mower pages, so this source is unsafe to automate

### `gtxservice.com`
- product sitemap is open:
  - `https://gtxservice.com/sitemap/pl-product-sitemap.xml`
- direct cards can have real media, example:
  - `https://gtxservice.com/pl/rekojesc-szt-makita-273666-1.html`
- current honest tail sample result:
  - `0/60` via sitemap slug matching
- keep only as a possible niche fallback if a better article lookup path appears

### `makita.net.ua`
- strong new candidate
- search is open in both locales:
  - `https://makita.net.ua/ru/search?search_query={ARTICLE}`
  - `https://makita.net.ua/uk/search?search_query={ARTICLE}`
- sitemap index is also open:
  - `https://makita.net.ua/1_index_sitemap.xml`
- direct product pages expose real article-coded product links and real product images, example:
  - `https://makita.net.ua/ru/6857-derzhatel-nozha-dlm462-makita-original-319882-2`
  - `https://makita.net.ua/25227-ws-store_large/trimach-nozha-dlm462-makita-orignal-319882-2.jpg`
- current honest tail sample result:
  - `27/60` exact useful hits
- full iteration result:
  - input `389`
  - confirmed folders `62` after manual review
  - honest remainder `327`
- working approach:
  - search only through the open Prestashop result page
  - keep only exact article-coded product links
  - on the product card trust only the main `og:image` / `ws-store_large` image
  - stay conservative and do not pull recommendation-block images
- manual review note:
  - some accepted cards used third-party sourced images with watermarks
  - those folders were removed manually and the honest remainder was rebuilt from actual surviving folders

### `elektroserw.com.pl`
- exact article-coded product pages are easy to find, example:
  - `https://elektroserw.com.pl/makita-3-adapter-koncowki-do-af505-numer-katalogowy-hy00000378-p-183149.html`
- current honest tail sample result:
  - `9/30`
- rejection reason:
  - sampled cards all expose the same generic image:
    - `https://elektroserw.com.pl/images/images/makita-miniaturka.jpg`
  - do not use for production imports

### `leitermann.de`
- sitemap is open and product pages are reachable
- exact public search-engine hits exist for some Makita accessory part numbers
- current honest tail sample result:
  - `0/40` via sitemap matching
- sampled product/media pages are too noisy and unreliable for efficient automation on the current tail

### `makita.sklep.pl`
- sitemap is open and exact part-number cards exist
- rejection reason:
  - sampled product images are watermarked

### `makita-ua.com.ua`
- sitemap index is open:
  - `https://makita-ua.com.ua/sitemap.xml`
- working search endpoint:
  - `https://makita-ua.com.ua/poisk-po-saytu?search_api_fulltext={ARTICLE}`
- sampled product cards are clean and use real `og:image`
- current honest tail sample result:
  - `2/40`
- too thin for a full iteration right now, but worth keeping as a niche fallback

### `makitauae.com`
- Yoast sitemap index is open:
  - `https://makitauae.com/sitemap.xml`
- product sitemap files are public and can be scanned for exact part numbers
- current honest tail sample result:
  - `3/60`
- still only a niche fallback, not a mass-coverage source

### `maklta.com.ua`
- sitemap is open:
  - `https://maklta.com.ua/sitemap.xml`
- working approach:
  - map articles through exact slug-containing sitemap URLs
  - keep only cards that expose real product images under:
    - `/image/catalog/...`
    - `/userfiles/image/catalog/...`
  - keep only image paths that also contain the article token
- full iteration result:
  - input `327`
  - confirmed folders `22` after manual review
  - honest remainder `306`
- this source is narrow but clean enough to keep as a valid completed layer

### `szerszamkell.hu`
- sitemap index is open:
  - `https://www.szerszamkell.hu/sitemap.xml`
- isolated clean direct cards do exist, example:
  - `https://www.szerszamkell.hu/makita_632c23-4_li-ion_akku_108v_15ah_136184`
- current honest tail reality:
  - `0/306` exact article hits via sitemap scan
  - internal search pages echo the article but do not expose a usable exact-result path
- do not use on the current tail

### `robeks.si`
- isolated clean direct cards do exist, example:
  - `https://www.robeks.si/akumulator-makita%2C-10%2C8-v%2C-632c23-4`
- current honest tail sample:
  - `0/15` via local search
- too thin for a full iteration

### `zip4tools.ru`
- externally indexed exact part pages seem to exist, but direct shell requests return almost empty HTML
- local search paths tested:
  - `/search/?q={ARTICLE}`
  - `/search/index.php?query={ARTICLE}`
  - `/catalog/search/?q={ARTICLE}`
- current result:
  - no trustworthy searchable HTML
  - no stable `og:image` / media extraction path
- reject for automation

### `ersatzteil-service.de`
- exact part pages do exist for some articles, example:
  - `https://www.ersatzteil-service.de/artikel/messerhalter/gb00000132-mak`
- rejection reason:
  - sampled media falls back to:
    - `/bilder/artikelbilder/kein.jpg`
- do not use for production import

### `vmshop.cz`
- sitemap index is open:
  - `https://vmshop.cz/sitemap.xml`
- at least one clean exact card is confirmed:
  - `https://vmshop.cz/632c23-4/makita-632c23-4`
- confirmed clean media example:
  - `https://cdn.vmshop.cz/images/get/114/9939381.jpg`
- current issue:
  - current-tail sample coverage is still too weak
  - no scalable article-to-URL strategy is proven yet beyond isolated hits
- keep only as a later fallback

### `tatmart.com`
- sitemap index is open:
  - `https://www.tatmart.com/sitemap.xml`
- exact clean card example:
  - `https://www.tatmart.com/en/khoa-dau-khoan-s10-makita-763447-6-for-mt606.html`
- current honest tail reality:
  - about `3/100` on the current sample
- too thin for a full iteration

### `ultimamac.com`
- sitemap is open:
  - `https://ultimamac.com/sitemap.xml`
- product pages are real, but current-tail coverage in sitemap is `0`
- sampled cards lean on:
  - site logo in `og:image`
  - drawing/diagram media rather than clearly trustworthy product photos
- reject for automation

### `kirchner24.de`
- sitemap index is open:
  - `https://www.kirchner24.de/sitemap.xml`
- exact clean card example:
  - `https://www.kirchner24.de/makita-sperrschluessel-643535-4-fuer-elektro-rasenmaeher-dlm460_50414_16323/`
- current honest tail reality:
  - only `1` confirmed sitemap hit on the current tail (`643535-4`)
- keep only as a niche fallback

### `tkoutils.fr`
- real sitemap index is exposed in `robots.txt`:
  - `https://tkoutils.fr/1_index_sitemap.xml`
- exact URLs are plentiful, but sampled media is too dirty:
  - repeated placeholder hash `e954ec099d461c7df2f14b145f6208ae`
  - repeated secondary hash `ff06926a86e2805535370e1b5a4a593f`
- even though some cards are real, bulk use is unsafe

### `elektroservis-povse.com`
- exact clean card example:
  - `https://www.elektroservis-povse.com/orodje-za-vrt-in-gozd/kosilnice/816/pokrov-za-mulcenje-plm4618-plm4628n-plm4627n-671326001-10939/`
- problem:
  - local search pages echo the query and create a large false-positive wall
  - no proven clean lookup path from article to exact card yet
- reject for automation for now

### `trgovina-jana.si`
- sitemap index is open:
  - `https://trgovina-jana.si/sitemap.xml`
- exact clean card example:
  - `https://trgovina-jana.si/makita-671326001-pokrov-za-mulcenje`
- current honest tail reality:
  - `4/100` via sitemap scan
- too thin for a full iteration, but worth remembering as a niche fallback

### `mtools.be`
- sitemap index is open:
  - `https://www.mtools.be/sitemap/sitemap_be.xml`
- working approach:
  - resolve exact product URLs only from sitemap
  - reject all generic `makita_onderdelen_*.jpg` and `machine-onderdeel_*.png` style media unless the image filename itself contains the article token
  - this avoids a large block of repeated generic images that look like real files but collapse to the same hash
- full iteration result:
  - input `306`
  - confirmed folders `16`
  - honest remainder `290`
- safe examples:
  - `763447-6_c1c0.jpg`
  - `191n83-6_c1c0.jpg`
  - `821844-3_c1l0_s01.jpg`
- keep as a valid but narrow completed layer

### `thin_sources`
- separate layer for exact one-offs and very thin leftovers
- current collected articles:
  - `643535-4` from `kirchner24.de`
  - `671326001` from `trgovina-jana.si`
  - `671509001` from `trgovina-jana.si`
  - `671936001` from `trgovina-jana.si`
  - `TE00000335` from `tatmart.com`
  - `GB00000132` from `warenhandel.at`
  - `671002049` from `pitkiskone.fi`
- current result:
  - input `290`
  - confirmed folders `7` after manual review
  - honest remainder `283`
- note:
  - the three `trgovina-jana.si` entries intentionally share one image and should stay easy to spot for manual review

### `toolmax.nl`
- web search already shows exact accessory product pages
- examples found:
  - `134890-0`
  - `JM23100117`
  - `TE00000597`
- locally blocked by `403`, even with `cloudscraper`

### `mima.de`
- web search already shows exact article-coded Makita accessory pages
- examples found:
  - `TE00000597`
  - `191H11-5`
- currently blocked by protection page / `403`
