from __future__ import annotations
import re
import requests
from bs4 import BeautifulSoup
from report_files import build_local_reports

URLS=['https://finance.naver.com/research/company_list.naver','https://stock.naver.com/research/company']

def _metrics(text):
    t=' '.join((text or '').split()); target=None
    m=re.search(r'목표주가[^0-9]{0,25}([0-9][0-9,]{3,})\s*원?',t,re.I)
    if m:
        try: target=int(m.group(1).replace(',',''))
        except Exception: pass
    action='상향' if '상향' in t else '하향' if '하향' in t else None
    return target,action

def build_research(max_items=120):
    headers={'User-Agent':'Mozilla/5.0 (compatible; StockKingInvestmentOS/2.0)'}
    errors=[]; out=[]
    for url in URLS:
        try:
            r=requests.get(url,headers=headers,timeout=25); r.raise_for_status()
            soup=BeautifulSoup(r.text,'lxml')
            for tr in soup.select('table.type_1 tr'):
                tds=tr.select('td')
                if len(tds)<4: continue
                a=tr.select_one('a')
                if not a: continue
                text=' '.join(td.get_text(' ',strip=True) for td in tds)
                href=a.get('href','')
                if href.startswith('/'): href='https://finance.naver.com'+href
                code=None; m=re.search(r'code=(\d{6})',href); code=m.group(1) if m else None
                target,action=_metrics(text)
                out.append({'title':a.get_text(' ',strip=True),'text':text,'url':href,'code':code,'source':'NAVER Research','target_price':target,'target_action':action})
            if out: break
        except Exception as e: errors.append(f'{url}: {e}')
    local=build_local_reports(max_items=max_items)
    out.extend(local.get('items',[])); errors.extend(local.get('errors',[]))
    return {'status':'OK' if out else 'PENDING','errors':errors,'items':out[:max_items],
            'source_status':{'naver':'OK' if any(x.get('source')=='NAVER Research' for x in out) else 'PENDING','user_pdf':local.get('status')}}
