
from __future__ import annotations
from io import BytesIO
from pathlib import Path
from urllib.parse import quote_plus, urljoin
import re, time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from PIL import Image

BASE_DIR=Path(__file__).resolve().parent
INPUT_FILE=BASE_DIR/'output'/'current_tail_after_official_na_nz.xlsx'
OUTPUT_DIR=BASE_DIR/'output'/'import_images'
REPORT_FILE=BASE_DIR/'output'/'makitarussia_tail_report.xlsx'
COL_ARTICLE='Артикул [ARTIKUL]'; COL_NAME='Наименование элемента'
BASE='https://makitarussia.ru'
Image.MAX_IMAGE_PIXELS=None

def norm(v):
 if v is None or pd.isna(v): return ''
 return re.sub(r'\s+','',str(v).strip().upper())
def token(v): return re.sub(r'[^A-Z0-9]+','',str(v).upper())
def safe(v): return re.sub(r'[^\w\-.]+','_',str(v).strip())[:120]
def session():
 s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0','Accept-Language':'ru,en;q=0.9'}); return s
def prep(img):
 img=img.convert('RGBA' if img.mode in ('RGBA','LA') or (img.mode=='P' and 'transparency' in img.info) else 'RGB')
 img.thumbnail((1600,1600), Image.LANCZOS); return img
def dl(s,u,p):
 try:
  r=s.get(u,timeout=35)
  if r.status_code!=200 or len(r.content)<1000: return False, f'http_{r.status_code}_small'
  img=prep(Image.open(BytesIO(r.content))); p.parent.mkdir(parents=True,exist_ok=True); img.save(p,'WEBP',quality=84,method=6); return True,'ok'
 except Exception as e: return False,str(e)[:120]

def search(s, article):
 r=s.get(BASE+'/search/?query='+quote_plus(article), timeout=35)
 if r.status_code!=200: return None, [], f'http_{r.status_code}'
 soup=BeautifulSoup(r.text,'html.parser'); at=token(article); links=[]
 for a in soup.select('a[href]'):
  href=a.get('href') or ''; text=' '.join(a.get_text(' ',strip=True).split())
  if '/product/' not in href: continue
  if at not in token(href+' '+text): continue
  full=urljoin(BASE,href)
  if full not in links: links.append(full)
 for link in links:
  rr=s.get(link,timeout=35)
  if rr.status_code!=200 or at not in token(rr.text): continue
  ss=BeautifulSoup(rr.text,'html.parser')
  imgs=[]
  for node in ss.select("meta[property='og:image'], img[src], img[data-src], a[href]"):
   val=node.get('content') or node.get('data-src') or node.get('src') or node.get('href') or ''
   if not val: continue
   full=urljoin(link,val).split('?')[0]
   low=full.lower()
   if not re.search(r'\.(jpg|jpeg|png|webp)$',low): continue
   if 'logo' in low or 'placeholder' in low or 'icon_' in low or 'category' in low: continue
   if '/wa-data/public/shop/products/' not in low: continue
   if full not in imgs: imgs.append(full)
  if imgs: return link, imgs[:4], 'ok'
 return None, [], 'not_found'

def main():
 OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
 df=pd.read_excel(INPUT_FILE); rows=[]; s=session()
 for _,row in df.iterrows():
  art=norm(row.get(COL_ARTICLE)); name=str(row.get(COL_NAME,'')).strip()
  if not art: continue
  if (OUTPUT_DIR/safe(art)/'preview.webp').exists():
   rows.append({'article':art,'name':name,'source':'makitarussia.ru','status':'SKIP','note':'already_has_preview','product_url':'','images_found':0}); continue
  url,imgs,note=search(s,art); status='FAIL'; saved=0
  if imgs:
   folder=OUTPUT_DIR/safe(art)
   for i,u in enumerate(imgs):
    ok,reason=dl(s,u,folder/('preview.webp' if i==0 else f'gallery_{i:02d}.webp'))
    if ok: saved+=1
   if (folder/'preview.webp').exists(): status='OK'; note='ok'
  rows.append({'article':art,'name':name,'source':'makitarussia.ru','status':status,'note':note,'product_url':url or '','images_found':len(imgs),'saved':saved})
  time.sleep(.1)
 out=pd.DataFrame(rows); out.to_excel(REPORT_FILE,index=False); print(out['status'].value_counts(dropna=False).to_string())
if __name__=='__main__': main()
