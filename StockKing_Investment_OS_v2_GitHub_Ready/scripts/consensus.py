from __future__ import annotations
import csv
from common import ROOT, safe_float

def load_consensus():
    p=ROOT/'config'/'consensus.csv'; rows=[]
    if not p.exists(): return {'status':'PENDING','items':[]}
    with p.open(encoding='utf-8') as f:
        for r in csv.DictReader(line for line in f if not line.lstrip().startswith('#')):
            if not r.get('code'): continue
            num=['revenue_12mf','op_12mf','eps_12mf','target_price','revenue_revision_pct','op_revision_pct','eps_revision_pct','target_revision_pct']
            row={**r,'code':r['code'].zfill(6)}
            for k in num: row[k]=safe_float(r.get(k))
            rows.append(row)
    return {'status':'OK' if rows else 'PENDING','items':rows}
