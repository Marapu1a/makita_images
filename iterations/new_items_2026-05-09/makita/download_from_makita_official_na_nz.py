
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, quote
import re
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "output" / "current_tail_after_manual_review.xlsx"
OUTPUT_DIR = BASE_DIR / "output" / "import_images"
REPORT_FILE = BASE_DIR / "output" / "makita_official_na_nz_report.xlsx"
COL_ARTICLE = "Артикул [ARTIKUL]"
COL_NAME = "Наименование элемента"
SOURCE_NAME = "makita official NZ/Canada"

Image.MAX_IMAGE_PIXELS = None


def norm(v):
    if v is None or pd.isna(v):
        return ""
    return re.sub(r"\s+", "", str(v).strip().upper())


def token(v):
    return re.sub(r"[^A-Z0-9]+", "", str(v).upper())


def safe(v):
    return re.sub(r"[^\w\-.]+", "_", str(v).strip())[:120]


def make_session():
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0", "Accept-Language": "en,ru;q=0.9"})
    return s


def prepare(img):
    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    img = img.convert("RGBA" if has_alpha else "RGB")
    img.thumbnail((1600,1600), Image.LANCZOS)
    return img


def download(session, url, path):
    try:
        r = session.get(url, timeout=35)
        if r.status_code != 200 or len(r.content) < 1000:
            return False, f"http_{r.status_code}_or_small"
        img = Image.open(BytesIO(r.content))
        img = prepare(img)
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path, "WEBP", quality=84, method=6)
        return True, "ok"
    except Exception as e:
        return False, str(e)[:120]


def nz_search(session, article):
    r = session.post("https://www.makita.co.nz/search/", data={"a":"search", "searchTerm": article}, timeout=35)
    if r.status_code != 200:
        return None, [], f"nz_http_{r.status_code}"
    soup = BeautifulSoup(r.text, "html.parser")
    links = []
    atok = token(article)
    for a in soup.select("a[href]"):
        href = a.get("href") or ""
        text = " ".join(a.get_text(" ", strip=True).split())
        if "/accessories/item/" not in href and "/products/model/" not in href:
            continue
        if atok not in token(href + " " + text):
            continue
        full = urljoin("https://www.makita.co.nz", href)
        if full not in links:
            links.append(full)
    for link in links:
        rr = session.get(link, timeout=35)
        if rr.status_code != 200 or atok not in token(rr.text):
            continue
        ss = BeautifulSoup(rr.text, "html.parser")
        imgs = []
        for node in ss.select("a[href], img[src], meta[property='og:image']"):
            val = node.get("content") or node.get("src") or node.get("href") or ""
            if not val:
                continue
            full = urljoin(link, val).replace(" ", "%20")
            low = full.lower()
            if "images.makita.co.nz" not in low:
                continue
            if not re.search(r"\.(jpg|jpeg|png|webp)$", low):
                continue
            if atok not in token(full):
                continue
            if full not in imgs:
                imgs.append(full)
        if imgs:
            return link, imgs[:5], "ok"
    return None, [], "not_found_nz"


def canada_search(session, article):
    search_url = "https://www.makita.ca/index2new.php?event=searchprocess&searchkeyword={}&searchkeywordbox=other&searchkeywordid=&all_or_less=all&listlang=English".format(quote(article))
    r = session.get(search_url, timeout=35)
    if r.status_code != 200:
        return None, [], f"ca_http_{r.status_code}"
    soup = BeautifulSoup(r.text, "html.parser")
    atok = token(article)
    links=[]
    for a in soup.select("a[href]"):
        href=a.get("href") or ""
        text=" ".join(a.get_text(" ",strip=True).split())
        if "newaccessorydetailstemp" not in href and "event=tool" not in href:
            continue
        if atok not in token(href+" "+text):
            continue
        full=urljoin("https://www.makita.ca/", href)
        if full not in links: links.append(full)
    for link in links:
        rr=session.get(link,timeout=35)
        if rr.status_code!=200 or atok not in token(rr.text):
            continue
        imgs=[]
        # Canada uses filenames like './accessories/fullsize/1915P2-0 Photo 1.jpg'
        for m in re.finditer(r"(?:https?://[^\"']+|\./[^\"']+|/[^\"']+)\.(?:jpg|jpeg|png|webp)", rr.text, re.I):
            val=m.group(0)
            full=urljoin(link, val).replace(" ", "%20")
            low=full.lower()
            if "makita.ca" not in low or "accessories/fullsize" not in low:
                continue
            if atok not in token(full):
                continue
            if full not in imgs:
                imgs.append(full)
        if imgs:
            return link, imgs[:5], "ok"
    return None, [], "not_found_ca"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_excel(INPUT_FILE)
    rows=[]
    session=make_session()
    for _, row in df.iterrows():
        article=norm(row.get(COL_ARTICLE))
        name=str(row.get(COL_NAME,"")).strip()
        if not article:
            continue
        if (OUTPUT_DIR / safe(article) / "preview.webp").exists():
            rows.append({"article":article,"name":name,"source":SOURCE_NAME,"status":"SKIP","note":"already_has_preview","product_url":"","images_found":0})
            continue
        product_url, imgs, note = nz_search(session, article)
        source="makita.co.nz"
        if not imgs:
            product_url, imgs, note = canada_search(session, article)
            source="makita.ca"
        status="FAIL"; saved=0; save_note=note
        if imgs:
            folder=OUTPUT_DIR/safe(article)
            for i,u in enumerate(imgs):
                filename="preview.webp" if i==0 else f"gallery_{i:02d}.webp"
                ok, reason=download(session,u,folder/filename)
                if ok: saved+=1
                elif i==0: save_note=reason
            if (folder/"preview.webp").exists():
                status="OK"; save_note="ok"
        rows.append({"article":article,"name":name,"source":source,"status":status,"note":save_note,"product_url":product_url or "","images_found":len(imgs),"saved":saved})
        time.sleep(0.1)
    pd.DataFrame(rows).to_excel(REPORT_FILE,index=False)
    print(pd.DataFrame(rows)["status"].value_counts(dropna=False).to_string())

if __name__ == "__main__":
    main()
