from __future__ import annotations
import argparse, csv
from datetime import datetime
from common import ROOT, now_kst, read_json
from nxt import load_nxt
from market import build_market, build_indices
from dart import build_financials
from macro import build_macro
from news import build_news
from telegram import build_telegram
from research import build_research
from consensus import load_consensus
from tracking import save_snapshot, append_integrated_signals, build_tracking
from industries import build_industries
from signal_engine import build_integrated_signals
from close_report import build_close_report
from build import write_dashboard

def watchlist_codes():
    p=ROOT/'config'/'watchlist.csv'; out=[]
    if p.exists():
        with p.open(encoding='utf-8') as f:
            out=[r['code'].zfill(6) for r in csv.DictReader(f) if r.get('code')]
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--date',help='YYYYMMDD')
    ap.add_argument('--light',action='store_true',help='market refresh; preserve slow sources')
    ap.add_argument('--market-only',action='store_true',help='final market/flow refresh; preserve slow sources')
    ap.add_argument('--sources-only',action='store_true',help='refresh news/telegram/research/macro while reusing last market snapshot')
    args=ap.parse_args()
    prior=read_json(ROOT/'data'/'dashboard.json',{})

    if args.sources_only and prior.get('stocks'):
        date_iso=prior.get('meta',{}).get('asOf') or now_kst().strftime('%Y-%m-%d')
        stocks=prior.get('stocks',[]); industries=prior.get('industries') or build_industries(stocks)
        indices=prior.get('indices',{})
        nxt_source=(prior.get('meta',{}).get('sourceStatus') or {}).get('NXT','PENDING')
    else:
        end,stocks=build_market(requested=args.date,nxt_by_code={},include_flow=not args.light)
        date_iso=datetime.strptime(end,'%Y%m%d').strftime('%Y-%m-%d')
        nxt,nxt_source=load_nxt(date_iso)
        if nxt: end,stocks=build_market(requested=end,nxt_by_code=nxt,include_flow=not args.light)
        industries=build_industries(stocks); indices=build_indices(end)

    selected=[]
    for c in watchlist_codes()+[s['code'] for s in stocks[:20]]:
        if c not in selected: selected.append(c)

    slow_refresh=not (args.light or args.market_only)
    financials=build_financials(selected) if slow_refresh else prior.get('financials',{'status':'PENDING','reason':'awaiting full refresh','companies':{}})
    macro=build_macro() if slow_refresh else prior.get('macro',{'status':'PENDING','series':{},'framework':{}})
    news=build_news() if slow_refresh else prior.get('news',[])
    telegram=build_telegram() if slow_refresh else prior.get('telegram',{'status':'PENDING','items':[],'errors':[]})
    research=build_research() if slow_refresh else prior.get('research',{'status':'PENDING','items':[],'errors':[]})
    consensus=load_consensus()

    integrated=build_integrated_signals(stocks,industries,financials,consensus,research,news,telegram,macro)
    rows=integrated.get('rows',[])
    if not args.sources_only:
        save_snapshot(date_iso,stocks,rows)
        append_integrated_signals(date_iso,rows,threshold=72,min_confluence=3)
    tracking=build_tracking()
    close=build_close_report(stocks,industries,rows,indices)

    above60=sum(1 for s in stocks if s.get('above60')); high_signal=sum(1 for s in stocks if (s.get('score') or 0)>=70)
    breadth=round(above60/max(len(stocks),1)*100,1)
    macro_score=(macro.get('framework') or {}).get('macro_score') if isinstance(macro,dict) else None
    composite=round(max(0,min(100,0.65*breadth+0.35*(macro_score if macro_score is not None else 50))))
    regime='Risk-on' if composite>=65 else 'Neutral' if composite>=45 else 'Risk-off'
    source_status={
        'KRX':'OK','NXT':nxt_source,'DART':financials.get('status'),'12MF':consensus.get('status'),
        'NAVER_RESEARCH':research.get('status'),'TELEGRAM':telegram.get('status'),'MACRO':macro.get('status')}
    data={
      'meta':{'asOf':date_iso,'updatedAt':now_kst().isoformat(timespec='seconds'),'mode':'AUTO v2 · Integrated Signal Engine',
              'sourceStatus':source_status,'note':'Fact/Estimate/Interpretation 분리. 확보되지 않은 데이터는 PENDING.'},
      'market':{'regime':regime,'score':composite,'breadth60':breadth,'highSignal':high_signal,'universe':len(stocks),'nxtConnected':nxt_source=='OK'},
      'indices':indices,'closeReport':close,'integrated':integrated,
      'stocks':stocks,'industries':industries,'financials':financials,'consensus':consensus,'research':research,'news':news,
      'telegram':telegram,'macro':macro,'tracking':tracking
    }
    write_dashboard(data)
    print(f"built {date_iso}: stocks={len(stocks)}, integrated={len(rows)}, PRIME={sum(1 for x in rows if x['grade']=='PRIME')}, telegram={telegram.get('status')}")

if __name__=='__main__': main()
