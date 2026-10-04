from __future__ import annotations
import csv, io
import pandas as pd
import requests
from common import ROOT, safe_float

MAIN_URL='https://www.nextrade.co.kr/menu/transactionStatusMain/menuList.do'

def _normalize_code(v):
    s=''.join(ch for ch in str(v) if ch.isdigit())
    return s[-6:].zfill(6) if s else ''

def fetch_nxt_official():
    """Best-effort parser for NXT's public regular-market table.

    The public page is the primary source. If NXT changes rendering/API behavior,
    return an empty dataset and let the dashboard mark NXT as PENDING instead of
    fabricating values.
    """
    try:
        r=requests.get(MAIN_URL,timeout=30,headers={'User-Agent':'Mozilla/5.0 (StockKing Investment OS; public market data)'}); r.raise_for_status()
        tables=pd.read_html(io.StringIO(r.text))
    except Exception:
        return {}, 'PENDING'
    for df in tables:
        cols=[str(c).replace(' ','') for c in df.columns]
        if not any('종목코드' in c or 'Symbol' in c for c in cols):
            continue
        code_col=next((df.columns[i] for i,c in enumerate(cols) if '종목코드' in c or 'Symbol' in c),None)
        value_col=next((df.columns[i] for i,c in enumerate(cols) if '거래대금' in c or 'TradeValue' in c.replace(' ','')),None)
        vol_col=next((df.columns[i] for i,c in enumerate(cols) if '거래량' in c or 'TradingVolume' in c.replace(' ','')),None)
        if code_col is None or value_col is None: continue
        out={}
        for _,row in df.iterrows():
            code=_normalize_code(row.get(code_col))
            if not code: continue
            out[code]={'nxt_value':safe_float(row.get(value_col),0) or 0,'nxt_volume':safe_float(row.get(vol_col),0) or 0}
        if out: return out, 'OFFICIAL_WEB'
    return {}, 'PENDING'

def load_nxt_csv(date_iso):
    p=ROOT/'config'/'nxt_daily.csv'; out={}
    if not p.exists(): return out
    for row in csv.DictReader(line for line in p.open(encoding='utf-8') if not line.lstrip().startswith('#')):
        if row.get('date')!=date_iso: continue
        code=(row.get('code') or '').zfill(6)
        if not code: continue
        out[code]={k:safe_float(row.get(k),0) for k in ['nxt_value','nxt_volume','foreign_net_value','institution_net_value']}
    return out

def load_nxt(date_iso):
    live,source=fetch_nxt_official()
    if live: return live,source
    csvdata=load_nxt_csv(date_iso)
    return (csvdata,'CSV_ADAPTER') if csvdata else ({},'PENDING')
