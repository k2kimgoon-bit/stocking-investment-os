from __future__ import annotations
import io, os, zipfile, xml.etree.ElementTree as ET
from datetime import datetime
import requests
from common import env, safe_float

BASE='https://opendart.fss.or.kr/api'
REPORTS=[('11013','Q1'),('11012','Q2'),('11014','Q3'),('11011','Q4')]

def corp_map(api_key):
    r=requests.get(f'{BASE}/corpCode.xml',params={'crtfc_key':api_key},timeout=40); r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        root=ET.fromstring(z.read(z.namelist()[0]))
    out={}
    for item in root.findall('list'):
        code=(item.findtext('stock_code') or '').strip()
        if code: out[code.zfill(6)]=(item.findtext('corp_code') or '').strip()
    return out

def _fetch(api_key, corp_code, year, report):
    p={'crtfc_key':api_key,'corp_code':corp_code,'bsns_year':str(year),'reprt_code':report,'fs_div':'CFS'}
    r=requests.get(f'{BASE}/fnlttSinglAcntAll.json',params=p,timeout=30); r.raise_for_status(); j=r.json()
    if j.get('status')=='013':
        p['fs_div']='OFS'; r=requests.get(f'{BASE}/fnlttSinglAcntAll.json',params=p,timeout=30); r.raise_for_status(); j=r.json()
    return j.get('list') or []

def _account(rows, names):
    for n in names:
        for r in rows:
            if r.get('sj_div')!='IS': continue
            if (r.get('account_nm') or '').replace(' ','')==n.replace(' ',''):
                return safe_float(r.get('thstrm_amount'))
    # fallback substring
    for r in rows:
        if r.get('sj_div')!='IS': continue
        nm=(r.get('account_nm') or '').replace(' ','')
        if any(n.replace(' ','') in nm for n in names): return safe_float(r.get('thstrm_amount'))
    return None

def _quarterize(cum):
    out=[]; prior={}
    for x in sorted(cum,key=lambda z:(z['year'],z['qnum'])):
        y=x['year']; q=x['qnum']; cur=x['value']
        if cur is None: val=None
        elif q==1: val=cur
        elif q in (2,3): val=cur-(prior.get((y,q-1)) or 0)
        else: val=cur
        out.append({**x,'value':val}); prior[(y,q)]=cur
    return out

def get_8q(api_key, stock_code, corp_code, current_year=None):
    current_year=current_year or datetime.now().year
    raw=[]
    for year in range(current_year-2,current_year+1):
        for report,label in REPORTS:
            try:
                rows=_fetch(api_key,corp_code,year,report)
            except Exception:
                continue
            if not rows: continue
            qnum={'Q1':1,'Q2':2,'Q3':3,'Q4':4}[label]
            raw.append({'year':year,'quarter':label,'qnum':qnum,
                        'revenue_cum':_account(rows,['매출액','영업수익','수익(매출액)']),
                        'op_cum':_account(rows,['영업이익','영업이익(손실)']),
                        'net_cum':_account(rows,['당기순이익','당기순이익(손실)'])})
    if not raw: return []
    # Q4 annual amount must be annual minus Q1-Q3 cumulative when available.
    def standalone(key):
        items=[]; byy={}
        for x in raw:
            byy.setdefault(x['year'],{})[x['qnum']]=x.get(key)
        for x in raw:
            y,q=x['year'],x['qnum']; v=x.get(key)
            if v is None: sv=None
            elif q==1: sv=v
            elif q in (2,3): sv=v-(byy[y].get(q-1) or 0)
            else: sv=v-(byy[y].get(3) or 0)
            items.append((y,q,sv))
        return {(y,q):v for y,q,v in items}
    rev=standalone('revenue_cum'); op=standalone('op_cum'); net=standalone('net_cum')
    out=[]
    for x in raw:
        k=(x['year'],x['qnum']); r=rev.get(k); o=op.get(k); n=net.get(k)
        out.append({'period':f"{x['year']} {x['quarter']}",'revenue':r,'operating_income':o,'net_income':n,
                    'op_margin':None if r in (None,0) or o is None else round(o/r*100,2)})
    out=sorted(out,key=lambda x:(int(x['period'][:4]),int(x['period'][-1])))
    return out[-8:]

def build_financials(codes):
    key=env('DART_API_KEY')
    if not key: return {'status':'PENDING','reason':'DART_API_KEY 미설정','companies':{}}
    try: cmap=corp_map(key)
    except Exception as e: return {'status':'ERROR','reason':str(e),'companies':{}}
    companies={}
    for code in codes:
        corp=cmap.get(code)
        if not corp: continue
        try: companies[code]=get_8q(key,code,corp)
        except Exception: companies[code]=[]
    return {'status':'OK','reason':'Open DART','companies':companies}
