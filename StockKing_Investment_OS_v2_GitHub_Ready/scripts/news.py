from __future__ import annotations
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
import feedparser
from common import now_kst
from events import classify_event

DEFAULT_QUERIES=[
 '반도체 쇼티지 OR 공급부족 OR 병목', 'HBM CAPEX 증설', 'PCB AI 서버 증설', '데이터센터 전력 CAPEX',
 '반도체 장비 수주', '목표주가 상향 매출 전망', '가격 인상 공급 부족',
 'AI semiconductor shortage bottleneck', 'HBM capacity capex', 'data center power capex',
 '800G 1.6T PCB demand', 'semiconductor equipment orders', 'memory price increase supply shortage'
]

def build_news(lookback_hours=48,max_items=100):
    cutoff=now_kst()-timedelta(hours=lookback_hours); items=[]; seen=set()
    for q in DEFAULT_QUERIES:
        lang=('en','US','US:en') if any(ord(c)<128 for c in q) and not any('\uac00'<=c<='\ud7a3' for c in q) else ('ko','KR','KR:ko')
        hl,gl,ceid=lang
        url=f'https://news.google.com/rss/search?q={quote(q)}&hl={hl}&gl={gl}&ceid={ceid}'
        try: feed=feedparser.parse(url)
        except Exception: continue
        for e in feed.entries[:35]:
            title=getattr(e,'title',''); link=getattr(e,'link','')
            if not title or title in seen: continue
            seen.add(title)
            try:
                dt=datetime(*e.published_parsed[:6],tzinfo=timezone.utc).astimezone(cutoff.tzinfo)
                if dt<cutoff: continue
            except Exception: dt=None
            cls=classify_event(title)
            items.append({'published':dt.isoformat() if dt else None,'type':cls['type'],'score':cls['event_score'],
                          'polarity':cls['polarity'],'pqc':cls['pqc'],'title':title,'url':link,'query':q})
    items.sort(key=lambda x:((x['published'] or ''),x['score']),reverse=True)
    return items[:max_items]
