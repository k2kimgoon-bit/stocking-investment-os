from __future__ import annotations
import math
from datetime import datetime, timedelta
import pandas as pd
from common import safe_float, zscore, percentile, clamp


def latest_business_date(stock, requested=None):
    end=datetime.strptime(requested,'%Y%m%d') if requested else datetime.now()
    for i in range(12):
        d=(end-timedelta(days=i)).strftime('%Y%m%d')
        try:
            cap=stock.get_market_cap_by_ticker(d, market='ALL')
            if cap is not None and not cap.empty:
                return d, cap
        except Exception:
            continue
    raise RuntimeError('최근 KRX 영업일을 찾지 못했습니다.')


def _investor_flow(stock, code, start, end):
    out={'foreign_net_value':None,'institution_net_value':None,'foreign_3d':None,'foreign_5d':None,'institution_3d':None,'institution_5d':None}
    try:
        f=stock.get_market_trading_value_by_date(start,end,code,on='순매수')
        if f is None or f.empty: return out
        def col(cands):
            for c in cands:
                if c in f.columns: return pd.to_numeric(f[c], errors='coerce').fillna(0)
            return None
        foreign=col(['외국인합계','외국인'])
        inst=col(['기관합계','기관'])
        if foreign is not None:
            out['foreign_net_value']=float(foreign.iloc[-1]); out['foreign_3d']=float(foreign.tail(3).sum()); out['foreign_5d']=float(foreign.tail(5).sum())
        if inst is not None:
            out['institution_net_value']=float(inst.iloc[-1]); out['institution_3d']=float(inst.tail(3).sum()); out['institution_5d']=float(inst.tail(5).sum())
    except Exception:
        pass
    return out


def build_market(requested=None, min_market_cap=1_000_000_000_000, max_stocks=220, nxt_by_code=None, include_flow=True):
    try:
        from pykrx import stock
    except ImportError as e:
        raise RuntimeError('pykrx 미설치') from e
    end, cap = latest_business_date(stock, requested)
    end_dt=datetime.strptime(end,'%Y%m%d')
    start=(end_dt-timedelta(days=400)).strftime('%Y%m%d')
    flow_start=(end_dt-timedelta(days=14)).strftime('%Y%m%d')
    cap=cap.sort_values('시가총액',ascending=False)
    universe=cap[cap['시가총액']>=min_market_cap].head(max_stocks)
    kospi=set(stock.get_market_ticker_list(end,'KOSPI')); kosdaq=set(stock.get_market_ticker_list(end,'KOSDAQ'))
    rows=[]
    for code, crow in universe.iterrows():
        try:
            name=stock.get_market_ticker_name(code)
            o=stock.get_market_ohlcv_by_date(start,end,code)
            if o is None or len(o)<65: continue
            o=o.copy()
            for c in ['시가','고가','저가','종가','거래량','거래대금']:
                if c in o: o[c]=pd.to_numeric(o[c],errors='coerce')
            close=float(o['종가'].iloc[-1]); open_=float(o['시가'].iloc[-1]); high=float(o['고가'].iloc[-1]); low=float(o['저가'].iloc[-1])
            v=float(o['거래대금'].iloc[-1]); vol=float(o['거래량'].iloc[-1])
            v20=o['거래대금'].tail(20); v60=o['거래대금'].tail(60)
            avg20=float(v20.mean()); avg60=float(v60.mean())
            vol20=float(o['거래량'].tail(20).mean())
            prev=float(o['종가'].iloc[-2]); w=float(o['종가'].iloc[-6]) if len(o)>=6 else prev
            m20=float(o['종가'].tail(20).mean()); m60=float(o['종가'].tail(60).mean()); m120=float(o['종가'].tail(120).mean())
            ma240=float(o['종가'].tail(min(240,len(o))).mean())
            ret20=(close/float(o['종가'].iloc[-21])-1)*100 if len(o)>=21 else None
            ret60=(close/float(o['종가'].iloc[-61])-1)*100 if len(o)>=61 else None
            week=(close/w-1)*100
            day=(close/prev-1)*100
            value_ratio=v/max(avg20,1)
            accel=(float(o['거래대금'].tail(5).mean())/max(float(o['거래대금'].tail(20).mean()),1))
            clv=0 if high==low else ((close-low)-(high-close))/(high-low)
            gap=(open_/prev-1)*100 if prev else 0
            gap_hold=0 if open_==prev else (close-prev)/(open_-prev) if (open_-prev)!=0 else 0
            turn=float(v/max(float(crow['시가총액']),1))*100
            nxt=(nxt_by_code or {}).get(code,{})
            nxt_value=safe_float(nxt.get('nxt_value'),0) or 0
            total_value=v+nxt_value
            flows=_investor_flow(stock,code,flow_start,end) if include_flow else {'foreign_net_value':None,'institution_net_value':None,'foreign_3d':None,'foreign_5d':None,'institution_3d':None,'institution_5d':None}
            f_ratio=(safe_float(flows['foreign_net_value'],0) or 0)/max(total_value,1)*100
            i_ratio=(safe_float(flows['institution_net_value'],0) or 0)/max(total_value,1)*100
            # Signal score: value abnormality 35, persistence/accel 20, price quality 20, flow 15, trend 10
            z20=zscore(v20.tolist()); z60=zscore(v60.tolist()); p60=percentile(v60.tolist())
            abnormal=clamp(((z20 or 0)+1)*12 + ((z60 or 0)+1)*8 + max(0,value_ratio-1)*10,0,35)
            persistence=clamp(max(0,accel-0.8)*25,0,20)
            priceq=clamp((clv+1)*7 + max(-2,min(2,day))/2*3 + max(0,min(2,gap_hold))*2,0,20)
            flowq=clamp(max(-5,min(5,f_ratio+i_ratio))*1.5+7.5,0,15)
            trend=10 if close>m20>m60 else 6 if close>m60 else 2
            score=round(clamp(abnormal+persistence+priceq+flowq+trend))
            rows.append({
                'code':code,'name':name,'market':'KOSPI' if code in kospi else 'KOSDAQ' if code in kosdaq else 'OTHER',
                'price':round(close),'market_cap':int(crow['시가총액']),'day_pct':round(day,2),'week_pct':round(week,2),'ret20':None if ret20 is None else round(ret20,2),'ret60':None if ret60 is None else round(ret60,2),
                'krx_value':int(v),'nxt_value':int(nxt_value),'total_value':int(total_value),'value_ratio20':round(value_ratio,2),'value_accel':round(accel,2),
                'z20':None if z20 is None else round(z20,2),'z60':None if z60 is None else round(z60,2),'pct60':None if p60 is None else round(p60,1),'turnover_pct':round(turn,2),
                'clv':round(clv,2),'gap_pct':round(gap,2),'gap_hold':round(gap_hold,2),'above20':close>m20,'above60':close>m60,'above240':close>ma240 if len(o)>=240 else None,
                **{k:(None if vv is None else round(vv,0)) for k,vv in flows.items()},'foreign_ratio_pct':round(f_ratio,2),'institution_ratio_pct':round(i_ratio,2),
                'program_net_value':None,'score':score
            })
        except Exception as e:
            continue
    rows.sort(key=lambda x:(x.get('score',0),x.get('total_value',0)),reverse=True)
    return end, rows

def build_indices(end):
    """KRX broad index close snapshots. Fail-soft because index API can vary by pykrx version."""
    try:
        from pykrx import stock
        end_dt=datetime.strptime(end,'%Y%m%d'); start=(end_dt-timedelta(days=10)).strftime('%Y%m%d')
        out={}
        for name,ticker in [('KOSPI','1001'),('KOSDAQ','2001')]:
            try:
                d=stock.get_index_ohlcv_by_date(start,end,ticker)
                if d is None or len(d)<1: continue
                close=float(d['종가'].iloc[-1]); prev=float(d['종가'].iloc[-2]) if len(d)>1 else None
                out[name]={'close':round(close,2),'day_pct':None if prev in (None,0) else round((close/prev-1)*100,2)}
            except Exception:
                continue
        return out
    except Exception:
        return {}
