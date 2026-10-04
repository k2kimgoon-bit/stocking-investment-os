from __future__ import annotations
import re
from collections import defaultdict

EVENT_RULES = {
    'SHORTAGE': (['쇼티지','공급부족','공급 부족','부족','병목','리드타임','품귀','shortage','bottleneck','lead time'], 86),
    'PRICE_UP': (['가격 인상','가격인상','단가 인상','단가인상','가격 상승','asp 상승','asp 인상'], 84),
    'CAPEX': (['증설','설비투자','capex','신규라인','착공','생산능력 확대','capacity expansion'], 78),
    'ORDER': (['수주','공급계약','계약 체결','납품','발주','order','contract'], 80),
    'REVISION_UP': (['목표주가 상향','추정치 상향','컨센서스 상향','실적 상향','상향 조정','earnings revision'], 84),
    'NEW_BIZ': (['신사업','신규 사업','신제품','양산 개시','양산 시작','신규 고객','고객사 확대'], 72),
    'POLICY': (['정책','보조금','규제 완화','세액공제','관세','법안'], 62),
    'DEMAND': (['수요 증가','수요 확대','판매 증가','출하 증가','가동률 상승','주문 증가'], 70),
    'NEGATIVE': (['감산','수요 둔화','주문 취소','가격 하락','단가 하락','목표주가 하향','추정치 하향','실적 하향','공급과잉','재고 증가'], 82),
}

P_WORDS=['가격','단가','asp','판가','가격 인상','가격 상승','스프레드']
Q_WORDS=['수요','출하','판매','수주','발주','증설','생산능력','가동률','고객','납품','물량','capacity','volume']
C_WORDS=['원가','비용','원재료','수율','인건비','전력비','물류비','감가상각','cost']
NEG_WORDS=['하락','둔화','감소','취소','하향','과잉','악화','적자','감산']


def classify_event(text:str):
    t=(text or '').lower()
    best=('NEWS',45,0)
    for typ,(words,base) in EVENT_RULES.items():
        hits=sum(1 for w in words if w.lower() in t)
        if hits and base+min(12,(hits-1)*4)>best[1]:
            best=(typ,min(100,base+min(12,(hits-1)*4)),hits)
    polarity=-1 if best[0]=='NEGATIVE' or any(w in t for w in NEG_WORDS) else 1
    pqc=[]
    if any(w in t for w in P_WORDS): pqc.append('P')
    if any(w in t for w in Q_WORDS): pqc.append('Q')
    if any(w in t for w in C_WORDS): pqc.append('C')
    return {'type':best[0],'event_score':best[1],'hits':best[2],'polarity':polarity,'pqc':pqc}


def entity_matches(text, stocks, industry_map):
    """Return matched stock codes + industries using exact Korean company names and light aliases."""
    t=(text or '').lower().replace(' ','')
    codes=[]
    for s in stocks:
        name=(s.get('name') or '').lower().replace(' ','')
        if len(name)>=2 and name in t:
            codes.append(s['code'])
    inds=[]
    for name,cfg in industry_map.items():
        keys=[name]+list(cfg.get('keywords',[]))
        if any(str(k).lower().replace(' ','') in t for k in keys if k):
            inds.append(name)
    # If an industry is explicitly matched, connect its members only as contextual exposure, not direct mention.
    return list(dict.fromkeys(codes)), list(dict.fromkeys(inds))


def aggregate_events(items, stocks, industry_map, source, base_confidence):
    """Normalize arbitrary title/text items into scored, entity-mapped events."""
    out=[]
    for idx,x in enumerate(items or []):
        text=' '.join(str(x.get(k) or '') for k in ('title','text','message','summary'))
        cls=classify_event(text)
        codes,inds=entity_matches(text,stocks,industry_map)
        explicit=str(x.get('code') or '').zfill(6) if x.get('code') else None
        valid_codes={s.get('code') for s in stocks}
        if explicit and explicit in valid_codes and explicit not in codes: codes.insert(0,explicit)
        direct=bool(codes)
        out.append({
            'id':f'{source}-{idx}', 'source':source, 'confidence':base_confidence,
            'title':x.get('title') or (x.get('message') or '')[:120], 'text':text[:1200],
            'url':x.get('url') or x.get('link'), 'published':x.get('published') or x.get('date'),
            'type':cls['type'],'event_score':cls['event_score'],'polarity':cls['polarity'],'pqc':cls['pqc'],
            'codes':codes,'industries':inds,'direct':direct,
        })
    return out
