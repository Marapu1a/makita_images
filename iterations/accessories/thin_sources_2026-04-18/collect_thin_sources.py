from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import time

import pandas as pd
import requests
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "input" / "pictures.xlsx"
OUTPUT_DIR = BASE_DIR / "output" / "import_images"
REPORT_FILE = BASE_DIR / "output" / "thin_sources_report.xlsx"

COL_ARTICLE = "Артикул [ARTIKUL]"
COL_NAME = "Наименование элемента"

REQUEST_TIMEOUT = 40
DOWNLOAD_RETRIES = 2
RETRY_SLEEP = 0.5
MIN_BYTES = 1500

WEBP_QUALITY = 82
WEBP_METHOD = 6
MAX_WIDTH = 1600
MAX_HEIGHT = 1600

Image.MAX_IMAGE_PIXELS = None


MANIFEST = [
    {
        "source": "kirchner24.de",
        "article": "643535-4",
        "product_url": "https://www.kirchner24.de/makita-sperrschluessel-643535-4-fuer-elektro-rasenmaeher-dlm460_50414_16323/",
        "image_url": "https://cdn02.plentymarkets.com/alf4tnzwtu1y/item/images/50414/full/Makita-Sperrschluessel-DLM460-643535-4.jpg",
        "note": "thin_exact_card",
    },
    {
        "source": "trgovina-jana.si",
        "article": "671326001",
        "product_url": "https://trgovina-jana.si/makita-671326001-pokrov-za-mulcenje",
        "image_url": "https://trgovina-jana.si/image/cache/catalog/image/catalog/orodje-in-mehanizacija/pribor/pribor-orodja-za-uporabo-na-prostem/kosilnice/671469001-1000x1000.jpg",
        "note": "thin_exact_card_shared_image",
    },
    {
        "source": "trgovina-jana.si",
        "article": "671509001",
        "product_url": "https://trgovina-jana.si/makita-671509001-pokrov-za-mulcenje",
        "image_url": "https://trgovina-jana.si/image/cache/catalog/image/catalog/orodje-in-mehanizacija/pribor/pribor-orodja-za-uporabo-na-prostem/kosilnice/671469001-1000x1000.jpg",
        "note": "thin_exact_card_shared_image",
    },
    {
        "source": "trgovina-jana.si",
        "article": "671936001",
        "product_url": "https://trgovina-jana.si/makita-671936001-orodje-za-mulcenje",
        "image_url": "https://trgovina-jana.si/image/cache/catalog/image/catalog/orodje-in-mehanizacija/pribor/pribor-orodja-za-uporabo-na-prostem/kosilnice/671469001-1000x1000.jpg",
        "note": "thin_exact_card_shared_image",
    },
    {
        "source": "tatmart.com",
        "article": "TE00000335",
        "product_url": "https://www.tatmart.com/dau-noi-makita-te00000335-for-mp100dcms.html",
        "image_url": "https://cdn.tatmart.com/images/detailed/59/MAKITA_TE00000335.jpg",
        "note": "thin_exact_card",
    },
    {
        "source": "warenhandel.at",
        "article": "GB00000132",
        "product_url": "https://www.warenhandel.at/index.php/shop/maschinen-e-ger%C3%A4te/makita/ma-ersatzteile/ma-gartenger%C3%A4te/ersatzteile-rasenm%C3%A4her/makita-gb00000132-messerflansch-halter-f%C3%BCr-dlm330-detail",
        "image_url": "https://www.warenhandel.at/images/stories/virtuemart/product/GB00000132ET.jpg",
        "note": "thin_exact_card",
    },
    {
        "source": "pitkiskone.fi",
        "article": "671002049",
        "product_url": "https://pitkiskone.fi/p/9001/varaosat/terat-ruohonleikkureihin/teraistukat-ja-terakiinnikkeet-tasoleikkureihin/teraistukka-plm5121-makita",
        "image_url": "https://pitkiskone.fi/dataflow/pitkiskone2/files/media/671002049teristukkamakitaplm5121_5626.jpg",
        "note": "thin_exact_card",
    },
    {
        "source": "maquinaespecialista.cl",
        "article": "632H78-9",
        "product_url": "https://maquinaespecialista.cl/bateriascargadores-makita/2507-bateria-bl1813g-18v-15-ah-li-ion-linea-eco-632h78-9-makita",
        "image_url": "https://maquinaespecialista.cl/2934-large_default/bateria-bl1813g-18v-15-ah-li-ion-linea-eco-632h78-9-makita.webp",
        "note": "thin_exact_card",
    },
    {
        "source": "webmotoculture.com",
        "article": "459811-4",
        "product_url": "https://www.webmotoculture.com/support-lame-tondeuse-makita/23993-support-de-lame-tondeuse-a-batterie-makita-dlm382-2100000737567.html",
        "image_url": "https://www.webmotoculture.com/102157-large_default/support-de-lame-tondeuse-a-batterie-makita-dlm382.jpg",
        "note": "thin_exact_card",
    },
    {
        "source": "karkkainen.com",
        "article": "126130-0",
        "product_url": "https://www.karkkainen.com/verkkokauppa/makita-126130-0-123258-5-side-handle-apukahva",
        "image_url": "https://img.karkkainen.com/images/e_trim:4/c_pad,f_auto,h_320,q_auto,w_260/v1/tuotekuvat/2050004011159_1/makita-126130-0-123258-5-side-handle.jpg",
        "note": "thin_exact_card",
    },
    {
        "source": "gartengeraete-onlineshop.de",
        "article": "192075-4",
        "product_url": "https://www.gartengeraete-onlineshop.de/makita-schnellspannbohrfutter-10mm-192075-4-artnumber-192075-4",
        "image_url": "https://cdn.gartengeraete-onlineshop.de/product/b845ca/makita-192075-4-c2l0/schnellspannbohrfutter-10mm-192075-4-produktbild.jpg?auto=format&h=500&w=750",
        "note": "thin_exact_card",
    },
]


def normalize_article(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().upper()


def safe_name(value: object) -> str:
    text = str(value).strip()
    text = re.sub(r"[^\w\-.]+", "_", text)
    return text[:120]


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/135.0.0.0 Safari/537.36"
            )
        }
    )
    return session


def prepare_image_for_webp(image: Image.Image) -> Image.Image:
    has_alpha = image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)
    image = image.convert("RGBA" if has_alpha else "RGB")
    image.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.LANCZOS)
    return image


def download_and_compress_image(url: str, target_path: Path, session: requests.Session) -> tuple[bool, str]:
    last_reason = "unknown"
    for _ in range(DOWNLOAD_RETRIES + 1):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                last_reason = f"http_{response.status_code}"
                raise ValueError(last_reason)
            if len(response.content) < MIN_BYTES:
                last_reason = "too_small"
                raise ValueError(last_reason)
            image = Image.open(BytesIO(response.content))
            image = prepare_image_for_webp(image)
            image.save(target_path, format="WEBP", quality=WEBP_QUALITY, method=WEBP_METHOD)
            return True, "ok"
        except Exception as exc:
            if str(exc).strip():
                last_reason = str(exc).strip()
            time.sleep(RETRY_SLEEP)
    return False, last_reason


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(INPUT_FILE)
    df[COL_ARTICLE] = df[COL_ARTICLE].map(normalize_article)
    df = df[df[COL_ARTICLE].astype(bool)].copy()
    df.reset_index(drop=True, inplace=True)

    names = {
        normalize_article(row[COL_ARTICLE]): str(row.get(COL_NAME, "")).strip()
        for _, row in df.iterrows()
        if normalize_article(row.get(COL_ARTICLE, ""))
    }
    current_articles = set(names)

    session = make_session()
    rows: list[dict] = []

    for item in MANIFEST:
        article = normalize_article(item["article"])
        if article not in current_articles:
            continue

        item_dir = OUTPUT_DIR / safe_name(article)
        item_dir.mkdir(parents=True, exist_ok=True)

        ok, note = download_and_compress_image(item["image_url"], item_dir / "preview.webp", session)
        status = "OK" if ok else "FAIL"
        rows.append(
            {
                "source": item["source"],
                "article": article,
                "name": names.get(article, ""),
                "status": status,
                "note": item["note"] if ok else f"download_failed:{note}",
                "product_url": item["product_url"],
                "image_url": item["image_url"],
            }
        )

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_excel(REPORT_FILE, index=False)
    print(f"thin_sources: written={len(rows)}")


if __name__ == "__main__":
    main()
