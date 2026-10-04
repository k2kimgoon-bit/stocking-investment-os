from __future__ import annotations
import io
from datetime import datetime, timedelta
import pandas as pd
import requests
from common import safe_float

SERIES={
 'cpi':'CPIAUCSL','unemployment':'UNRATE','us10y':'DGS10','sp500':'SP500','hy_spread':'BAMLH0A0HYM2','dollar':'DTWEXBGS'
}

def fetch_fred(series):
    url='https://fred.stlouisfed.org/graph/fredgraph.csv'
    r=requests.get(url,params={'id':series},timeout=30,headers={'User-Agent':'StockKing-Investment-OS/1.0'}); r.raise_for_status()
    df=pd.read_csv(io.StringIO(r.text)); df.columns=['date','value']; df['value']=pd.to_numeric(df['value'],errors='coerce'); df=df.dropna()
    return df

def _last(df): return float(df['value'].iloc[-1]) if len(df) else None

def build_macro():
    raw={}; errors=[]
    for k,s in SERIES.items():
        try: raw[k]=fetch_fred(s)
        except Exception as e: errors.append(f'{k}:{e}')
    out={'status':'OK' if raw else 'ERROR','errors':errors,'series':{},'framework':{}}
    for k,df in raw.items():
        vals=df.tail(100)
        out['series'][k]={'date':str(vals['date'].iloc[-1]),'value':round(_last(vals),4),'prev':round(float(vals['value'].iloc[-2]),4) if len(vals)>1 else None}
    # Lee Eun-taek style core checks: CPI 3m direction, unemployment 3m mean, 10Y 3m change, S&P price trend.
    if 'cpi' in raw:
        d=raw['cpi'].tail(4); out['framework']['cpi_3m_direction']='상승' if len(d)>=4 and d['value'].iloc[-1]>d['value'].iloc[-4] else '하락/보합'
        out['framework']['cpi_3m_pct']=round((d['value'].iloc[-1]/d['value'].iloc[-4]-1)*100,2) if len(d)>=4 else None
    if 'unemployment' in raw:
        d=raw['unemployment'].tail(6); cur=float(d['value'].tail(3).mean()) if len(d)>=3 else None; prev=float(d['value'].iloc[-6:-3].mean()) if len(d)>=6 else None
        out['framework']['unemployment_3m_avg']=None if cur is None else round(cur,2); out['framework']['unemployment_vs_prior3m']='악화' if cur is not None and prev is not None and cur>prev else '개선/보합'
    if 'us10y' in raw:
        d=raw['us10y'].tail(66); out['framework']['us10y_3m_change_bp']=round((float(d['value'].iloc[-1])-float(d['value'].iloc[0]))*100,1) if len(d)>20 else None
    if 'sp500' in raw:
        d=raw['sp500'].tail(66); out['framework']['sp500_3m_pct']=round((float(d['value'].iloc[-1])/float(d['value'].iloc[0])-1)*100,2) if len(d)>20 else None
    score=50
    score += 8 if out['framework'].get('cpi_3m_direction')=='하락/보합' else -8
    score += 8 if out['framework'].get('unemployment_vs_prior3m')=='개선/보합' else -8
    y=out['framework'].get('us10y_3m_change_bp'); score += 6 if y is not None and y<0 else -4 if y is not None and y>30 else 0
    sp=out['framework'].get('sp500_3m_pct'); score += 10 if sp is not None and sp>0 else -10 if sp is not None else 0
    out['framework']['macro_score']=max(0,min(100,score))
    return out
