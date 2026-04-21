# mtools.be

Working input:
- `input/pictures.xlsx`

Working idea:
- use `https://www.mtools.be/sitemap/sitemap_be.xml`
- resolve only exact product URLs whose slug contains the article
- trust only product images whose own filename also contains the same article token

Reason for strict filtering:
- many `mtools.be` cards use repeated generic images like `makita_onderdelen_*.jpg`
- these generic files are visually different names but identical by hash
- only article-coded media files are safe enough for this source

Outputs:
- `output/import_images`
- `output/mtools_be_report.xlsx`
- `output/remaining_after_mtools_be.xlsx`
