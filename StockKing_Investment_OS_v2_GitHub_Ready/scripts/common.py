from __future__ import annotations
import json, math, os, pathlib, statistics
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
CONFIG = ROOT / 'config'
HISTORY = DATA / 'history'
KST = ZoneInfo('Asia/Seoul')

for p in (DATA, HISTORY): p.mkdir(parents=True, exist_ok=True)

def now_kst(): return datetime.now(KST)
def iso_date(dt=None): return (dt or now_kst()).strftime('%Y-%m-%d')
def ymd(dt=None): return (dt or now_kst()).strftime('%Y%m%d')

def safe_float(v, default=None):
    try:
        if v is None: return default
        f=float(str(v).replace(',','').replace('%','').strip())
        return default if math.isnan(f) or math.isinf(f) else f
    except Exception: return default

def safe_int(v, default=None):
    f=safe_float(v)
    return default if f is None else int(f)

def zscore(values, current=None):
    vals=[safe_float(x) for x in values]
    vals=[x for x in vals if x is not None]
    if len(vals)<5: return None
    cur=vals[-1] if current is None else safe_float(current)
    if cur is None: return None
    m=statistics.fmean(vals); sd=statistics.pstdev(vals)
    return 0.0 if sd==0 else (cur-m)/sd

def percentile(values, current=None):
    vals=[safe_float(x) for x in values]
    vals=[x for x in vals if x is not None]
    if not vals: return None
    cur=vals[-1] if current is None else safe_float(current)
    if cur is None: return None
    return 100*sum(x<=cur for x in vals)/len(vals)

def clamp(v, lo=0, hi=100): return max(lo,min(hi,v))

def read_json(path, default=None):
    p=pathlib.Path(path)
    if not p.exists(): return {} if default is None else default
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return {} if default is None else default

def write_json(path, obj):
    p=pathlib.Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

def env(name, default=None):
    v=os.getenv(name)
    return default if v is None or v=='' else v
