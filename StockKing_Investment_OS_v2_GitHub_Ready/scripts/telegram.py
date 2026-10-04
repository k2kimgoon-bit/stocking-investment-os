from __future__ import annotations
import csv, re, hashlib
import requests
from bs4 import BeautifulSoup
from common import ROOT


def _sources():
    p=ROOT/'config'/'telegram_sources.csv'; out=[]
    if not p.exists(): return out
    with p.open(encoding='utf-8') as f:
        for r in csv.DictReader(line for line in f if not line.lstrip().startswith('#')):
            u=(r.get('channel') or '').strip().lstrip('@')
            if u: out.append({'channel':u,'label':(r.get('label') or u).strip()})
    return out


def _norm(text):
    t=re.sub(r'https?://\S+',' ',text or '')
    t=re.sub(r'\s+',' ',t).strip().lower()
    return re.sub(r'[^0-9a-z가-힣]+','',t)[:500]


def _parse_public(channel, label, max_per_channel=25):
    url=f'https://t.me/s/{channel}'
    r=requests.get(url,headers={'User-Agent':'Mozilla/5.0 (compatible; StockKingInvestmentOS/2.0)'},timeout=25)
    r.raise_for_status(); soup=BeautifulSoup(r.text,'lxml'); out=[]
    for wrap in soup.select('.tgme_widget_message_wrap')[-max_per_channel:]:
        msg=wrap.select_one('.tgme_widget_message_text')
        if not msg: continue
        text=msg.get_text(' ',strip=True)
        a=wrap.select_one('a.tgme_widget_message_date'); time=wrap.select_one('time')
        links=[]
        for la in msg.select('a[href]'):
            href=la.get('href') or ''
            if href.startswith('http') and 't.me/' not in href: links.append(href)
        out.append({'channel':label,'channel_id':channel,'message':text,'url':a.get('href') if a else url,
                    'source_links':list(dict.fromkeys(links))[:5],'published':time.get('datetime') if time else None})
    return out


def _dedupe(items):
    groups={}
    for x in items:
        key=hashlib.sha1(_norm(x.get('message','')).encode()).hexdigest() if _norm(x.get('message','')) else x.get('url')
        if key not in groups:
            groups[key]={**x,'channels':[x.get('channel')],'repost_count':1}
        else:
            g=groups[key]; g['repost_count']+=1
            if x.get('channel') not in g['channels']: g['channels'].append(x.get('channel'))
            g['source_links']=list(dict.fromkeys((g.get('source_links') or [])+(x.get('source_links') or [])))[:8]
    return list(groups.values())


def build_telegram(max_items=150):
    src=_sources()
    if not src: return {'status':'PENDING','reason':'config/telegram_sources.csv에 공개 채널을 등록하세요.','items':[],'errors':[]}
    raw=[]; errors=[]
    for s in src:
        try: raw.extend(_parse_public(s['channel'],s['label']))
        except Exception as e: errors.append(f"{s['channel']}: {e}")
    out=_dedupe(raw); out.sort(key=lambda x:x.get('published') or '',reverse=True)
    return {'status':'OK' if out else 'PENDING','reason':'public Telegram preview; repost dedup enabled',
            'items':out[:max_items],'errors':errors,'channels_configured':len(src),'raw_count':len(raw),'dedup_count':len(out)}
