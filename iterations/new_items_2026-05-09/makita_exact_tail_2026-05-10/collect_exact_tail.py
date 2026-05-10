from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import requests
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
IMPORT_DIR = OUTPUT_DIR / "import_images"
INPUT_XLSX = Path(__file__).resolve().parents[3] / "new_items_delivery_2026-05-09" / "remaining_placeholders.xlsx"
REPORT_XLSX = OUTPUT_DIR / "makita_exact_tail_report.xlsx"
REMAINING_XLSX = OUTPUT_DIR / "remaining_after_makita_exact_tail.xlsx"

HEADERS = {"User-Agent": "Mozilla/5.0"}

EXACT_MATCHES: dict[str, dict[str, str]] = {
    "191B17-7": {
        "source": "mastertools.nl",
        "source_url": "https://mastertools.nl/nl_nl/product/makita-geleiderail-adapter-191b17-7",
        "image_url": "https://api.mastertools.nl/media/catalog/product/cache/4ac98b0d5e81b56bd000310ba88c60e0/1/9/191b17-7_c1r0.jpg",
    },
    "632U95-7": {
        "source": "proforce.by",
        "source_url": "https://proforce.by/catalog/akkumulyator-makita-cxt-bl-1050b-12-0-v-5-0-a-ch-li-ion-2/",
        "image_url": "https://proforce.by/upload/iblock/be4/ci0mrdsx79u6q57jzq1glos7w0bbwa4k/akkumulyator_makita_cxt_bl_1050b_12_0_v_5_0_a_ch_li_ion.jpg",
    },
    "632R35-7": {
        "source": "makitaonline.cl",
        "source_url": "https://www.makitaonline.cl/bateria-bl4020-40v-20-ah-sin-caja-632r35-7-makita-632r35-7/p",
        "image_url": "https://makitaonline.vtexassets.com/arquivos/ids/157296/632R357_1.jpg",
    },
    "632S11-7": {
        "source": "line-tools.ru",
        "source_url": "https://line-tools.ru/catalog/akkumulyator-makita-bl1820g-632s11-7/",
        "image_url": "https://cdn.line-tools.ru/upload/resize_cache/iblock/73f/vkzyw7hc9wxni612yw2b61ao7hrsqt20/250_250_0/632S11-7.jpg",
    },
    "632S90-5": {
        "source": "sculeprime.ro",
        "source_url": "https://www.sculeprime.ro/product/bl4080f",
        "image_url": "https://www.sculeprime.ro/uploads/2025/09/0a5cd2080a2f3d87ecb801a5f16c25ec.jpg",
    },
    "191V54-1": {
        "source": "npower.com.vn",
        "source_url": "https://npower.com.vn/products/makita_191v541",
        "image_url": "https://npower.com.vn/cdn/shop/files/1_0001_Makita_191V541_1200x1200.jpg?v=1772118929",
    },
    "4131K6-6": {
        "source": "reposicaoonline.com.br",
        "source_url": "https://www.reposicaoonline.com.br/pre-filtro-4131k6-6/p/68857",
        "image_url": "https://static.reposicaoonline.com.br/public/reposicaoonline/imagens/produtos/pre-filtro-para-aspiradores-de-po-makita-4131k6-6-69b450b86688b.png",
    },
    "168406-9": {
        "source": "motozahrada.eu",
        "source_url": "https://www.motozahrada.eu/en/p/vodiaca-lista-makita-dolmar-25cm-3-8-1-3mm-40cl-168406-9-191g22-4-168408-5-74c",
        "image_url": "https://motozahrada-1.s33.cdn-upgates.com/_cache/e/1/e13bb3dee9b808d2f0721a86b4f93654-vyr-24979makita-lista.jpg",
    },
    "1916D0-6": {
        "source": "elvin.cz",
        "source_url": "https://www.elvin.cz/p/makita-1916d0-6-nuz-na-buren-3-zuby-255x25-4mm-old195299-1",
        "image_url": "https://elvin.s6.cdn-upgates.com/_cache/6/8/685950444735338a88343dc6e2545b4c-x6961e46d78576.jpeg",
    },
    "1916C9-1": {
        "source": "line-tools.ru",
        "source_url": "https://line-tools.ru/catalog/nozhi-trimmerov-makita/",
        "image_url": "https://cdn.line-tools.ru/upload/resize_cache/iblock/80e/yukmo19cwrm5fv6hvkjjzrld0fzhd7cm/250_250_0/1916C9-1.jpg",
    },
    "D-80298": {
        "source": "makitauae.com",
        "source_url": "https://makitauae.com/product/d-80298/",
        "image_url": "https://makitauae.com/wp-content/uploads/2025/07/D-80298.jpg",
    },
    "629387-7": {
        "source": "shopmancini.com",
        "source_url": "https://www.shopmancini.com/en/tools-accessories/7820-makita-18v-dc-replacement-motor-629387-7-629384-3-14-teeth-gear.html",
        "image_url": "https://www.shopmancini.com/33669-large_default/makita-18v-dc-replacement-motor-629387-7-629384-3-14-teeth-gear.jpg",
    },
    "620K10-3": {
        "source": "czescimakita.com",
        "source_url": "https://www.czescimakita.com/elektronika-makita-620k10-3-p-447699.html",
        "image_url": "https://www.czescimakita.com/images/czesci_makita_43/620K10-3-makita-80-1500.webp",
    },
}


def read_tail() -> pd.DataFrame:
    return pd.read_excel(INPUT_XLSX)


def save_preview(folder: Path, image_url: str) -> None:
    response = requests.get(image_url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    image = Image.open(BytesIO(response.content))
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA")
    if image.mode == "RGBA":
        background = Image.new("RGB", image.size, "white")
        background.paste(image, mask=image.getchannel("A"))
        image = background
    else:
        image = image.convert("RGB")
    folder.mkdir(parents=True, exist_ok=True)
    image.save(folder / "preview.webp", "WEBP", quality=90, method=6)


def main() -> None:
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    tail = read_tail()
    rows: list[dict[str, object]] = []

    for _, row in tail.iterrows():
        article = str(row["article"]).strip()
        meta = EXACT_MATCHES.get(article)
        out = {
            "project_block": row["project_block"],
            "article": article,
            "name": row["name"],
            "status": "FAIL",
            "source": "",
            "source_url": "",
            "image_url": "",
            "folder_name": article,
            "image_count": 0,
            "reason": "not_in_exact_matches",
        }
        if meta:
            folder = IMPORT_DIR / article
            save_preview(folder, meta["image_url"])
            out.update(
                {
                    "status": "OK",
                    "source": meta["source"],
                    "source_url": meta["source_url"],
                    "image_url": meta["image_url"],
                    "image_count": 1,
                    "reason": "",
                }
            )
        rows.append(out)

    report = pd.DataFrame(rows)
    report.to_excel(REPORT_XLSX, index=False)

    matched = {article for article, meta in EXACT_MATCHES.items() if (IMPORT_DIR / article / "preview.webp").exists()}
    remaining = tail[~tail["article"].astype(str).isin(matched)].copy()
    remaining.to_excel(REMAINING_XLSX, index=False)

    print(f"Collected exact matches: {len(matched)}")
    print(f"Remaining placeholders: {len(remaining)}")


if __name__ == "__main__":
    main()
