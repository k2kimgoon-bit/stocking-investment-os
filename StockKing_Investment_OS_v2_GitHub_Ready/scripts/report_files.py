from __future__ import annotations
import re
from pathlib import Path
from common import ROOT


def _extract_pdf(path:Path, max_pages=18):
    try:
        from pypdf import PdfReader
        r=PdfReader(str(path)); chunks=[]
        for p in r.pages[:max_pages]:
            try: chunks.append(p.extract_text() or '')
            except Exception: pass
        return '\n'.join(chunks)
    except Exception:
        return ''


def _metrics(text):
    t=' '.join((text or '').split())
    target=None
    m=re.search(r'목표주가[^0-9]{0,30}([0-9][0-9,]{3,})\s*원?',t,re.I)
    if m:
        try: target=int(m.group(1).replace(',',''))
        except Exception: pass
    action='상향' if '목표주가 상향' in t or '목표가 상향' in t else '하향' if '목표주가 하향' in t or '목표가 하향' in t else None
    kws=[]
    for w in ['쇼티지','병목','증설','CAPEX','수주','신사업','목표주가 상향','추정치 상향','2027','매출 성장','가격 인상']:
        if w.lower() in t.lower(): kws.append(w)
    return {'target_price':target,'target_action':action,'keywords':kws}


def build_local_reports(max_items=80):
    folder=ROOT/'inputs'/'reports'; items=[]; errors=[]
    if not folder.exists(): return {'status':'PENDING','items':[],'errors':[]}
    for p in sorted(folder.glob('*.pdf'), key=lambda x:x.stat().st_mtime, reverse=True)[:max_items]:
        text=_extract_pdf(p)
        if not text:
            errors.append(f'{p.name}: text extraction failed'); continue
        m=_metrics(text)
        items.append({'title':p.stem,'text':text[:14000],'url':f'inputs/reports/{p.name}','code':None,'source':'USER PDF',**m})
    return {'status':'OK' if items else 'PENDING','items':items,'errors':errors}
