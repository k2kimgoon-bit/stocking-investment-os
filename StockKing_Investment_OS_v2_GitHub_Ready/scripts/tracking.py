from __future__ import annotations
import csv
from common import HISTORY, read_json, write_json

SIGNALS=HISTORY/'signals.csv'
SNAP=HISTORY/'snapshots'
SNAP.mkdir(parents=True,exist_ok=True)
FIELDS=['date','code','name','d0_price','d0_score','confluence','grade']

def save_snapshot(date_iso, stocks, integrated=None):
    im={x['code']:x for x in (integrated or [])}
    write_json(SNAP/f'{date_iso}.json',{s['code']:{'price':s['price'],'market_score':s.get('score'),
        'integrated_score':(im.get(s['code']) or {}).get('integrated_score')} for s in stocks})

def _read_signals():
    if not SIGNALS.exists(): return []
    with SIGNALS.open(encoding='utf-8') as f: return list(csv.DictReader(f))

def append_integrated_signals(date_iso, rows, threshold=72, min_confluence=3):
    old=_read_signals(); keys={(r['date'],r['code']) for r in old}; new=[]
    for s in rows:
        if (s.get('integrated_score') or 0)<threshold or (s.get('confluence_count') or 0)<min_confluence: continue
        k=(date_iso,s['code'])
        if k in keys: continue
        new.append({'date':date_iso,'code':s['code'],'name':s['name'],'d0_price':s['price'],'d0_score':s['integrated_score'],
                    'confluence':s['confluence_count'],'grade':s['grade']})
    rows2=old+new
    if rows2:
        with SIGNALS.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=FIELDS,extrasaction='ignore'); w.writeheader(); w.writerows(rows2[-5000:])
    return rows2

def build_tracking(horizons=(1,3,5,10,20)):
    signals=_read_signals(); files=sorted(SNAP.glob('*.json')); dates=[p.stem for p in files]; snaps={p.stem:read_json(p,{}) for p in files}
    out=[]
    for r in signals[-1000:]:
        if r['date'] not in dates: continue
        i=dates.index(r['date']); d0=float(r['d0_price']); item={**r,'returns':{}}
        for h in horizons:
            if i+h < len(dates):
                rec=snaps[dates[i+h]].get(r['code']); p=(rec or {}).get('price')
                item['returns'][f'D+{h}']=None if p is None else round((float(p)/d0-1)*100,2)
            else: item['returns'][f'D+{h}']=None
        out.append(item)
    return out[-500:]
