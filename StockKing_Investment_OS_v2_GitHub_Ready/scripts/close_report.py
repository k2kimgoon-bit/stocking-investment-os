from __future__ import annotations
from statistics import fmean


def _pct(x): return '-' if x is None else f"{x:+.1f}%"

def build_close_report(stocks, industries, signal_rows, market_indices=None):
    if not stocks: return {'status':'PENDING','bullets':[],'leaders':[],'laggards':[]}
    adv=sum(1 for s in stocks if (s.get('day_pct') or 0)>0); dec=sum(1 for s in stocks if (s.get('day_pct') or 0)<0)
    avg=round(fmean([s.get('day_pct') or 0 for s in stocks]),2)
    topv=sorted(stocks,key=lambda x:x.get('total_value') or 0,reverse=True)[:5]
    leaders=sorted(industries,key=lambda x:x.get('strength') or 0,reverse=True)[:4]
    signals=sorted(signal_rows,key=lambda x:x.get('integrated_score') or 0,reverse=True)[:8]
    bullets=[
        f"대형주 유니버스 상승 {adv}개 / 하락 {dec}개, 단순평균 등락률 {_pct(avg)}.",
        "거래대금 상위: "+', '.join(f"{s['name']} {round((s.get('total_value') or 0)/1e8):,}억원" for s in topv),
        "강한 산업: "+', '.join(f"{x['name']}({x['strength']})" for x in leaders) if leaders else '산업 강도 데이터 PENDING.',
        "통합 신호 상위: "+', '.join(f"{x['name']} {x['integrated_score']}점/{x['confluence_count']}중첩" for x in signals) if signals else '통합 신호 없음.'
    ]
    if market_indices:
        idx=[]
        for k,v in market_indices.items():
            if v: idx.append(f"{k} {v.get('close','-')} ({_pct(v.get('day_pct'))})")
        if idx: bullets.insert(0,' / '.join(idx))
    return {'status':'OK','advance':adv,'decline':dec,'avg_day_pct':avg,'bullets':bullets,
            'leaders':[x['name'] for x in leaders], 'top_signals':[x['code'] for x in signals]}
