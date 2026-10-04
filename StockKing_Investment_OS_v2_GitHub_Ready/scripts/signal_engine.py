from __future__ import annotations
from collections import defaultdict
from statistics import fmean
from events import aggregate_events
from industries import MAP


def clamp(v,lo=0,hi=100): return max(lo,min(hi,v))

def _fund_score(qs):
    if not qs or len(qs)<5: return None, {'reason':'8분기 부족'}
    # Compare latest quarter with same quarter a year ago.
    a,b=qs[-1],qs[-5]
    def growth(k):
        x,y=a.get(k),b.get(k)
        if x is None or y in (None,0): return None
        return (x/y-1)*100
    rg=growth('revenue'); og=growth('operating_income')
    opm=a.get('op_margin'); opm0=b.get('op_margin'); dmargin=None if opm is None or opm0 is None else opm-opm0
    score=50
    if rg is not None: score += max(-20,min(20,rg/2))
    if og is not None: score += max(-20,min(20,og/2))
    if dmargin is not None: score += max(-10,min(10,dmargin*2))
    return round(clamp(score)), {'revenue_yoy':None if rg is None else round(rg,1),'op_yoy':None if og is None else round(og,1),'opm_delta':None if dmargin is None else round(dmargin,1)}

def _consensus_map(consensus):
    return {x.get('code'):x for x in (consensus or {}).get('items',[]) if x.get('code')}

def _cons_score(x):
    if not x: return None,{}
    # Preferred explicit revision columns; neutral if only level fields are supplied.
    vals=[]
    for k in ('revenue_revision_pct','op_revision_pct','eps_revision_pct','target_revision_pct'):
        try:
            if x.get(k) not in (None,''): vals.append(float(x[k]))
        except Exception: pass
    if not vals: return 55, {'reason':'수준 데이터만 존재; 리비전 미입력'}
    avg=fmean(vals); return round(clamp(55+avg*4)), {'revision_avg_pct':round(avg,2)}

def _source_score(events, code, industry_names):
    xs=[]
    for e in events:
        direct=code in e.get('codes',[])
        contextual=bool(set(industry_names)&set(e.get('industries',[])))
        if not (direct or contextual): continue
        mult=1.0 if direct else 0.45
        signed=e['event_score']*e.get('polarity',1)
        xs.append((signed*mult,e))
    if not xs: return None,[],0
    # strongest 5, diminishing returns; map signed evidence around neutral 50.
    xs.sort(key=lambda z:abs(z[0]),reverse=True); use=xs[:5]
    net=sum(v for v,_ in use)/(1+0.6*(len(use)-1))
    score=clamp(50+net*0.5)
    return round(score),[e for _,e in use],len(xs)

def build_integrated_signals(stocks, industries, financials, consensus, research, news, telegram, macro):
    sm={s['code']:s for s in stocks}; ind_by_code=defaultdict(list); ind_score={}
    for ind in industries:
        ind_score[ind['name']]=ind.get('strength') or 50
        for c in ind.get('members',[]): ind_by_code[c].append(ind['name'])
    news_ev=aggregate_events(news or [],stocks,MAP,'NEWS',0.72)
    tel_ev=aggregate_events((telegram or {}).get('items',[]),stocks,MAP,'TELEGRAM',0.52)
    rep_ev=aggregate_events((research or {}).get('items',[]),stocks,MAP,'RESEARCH',0.82)
    all_events=news_ev+tel_ev+rep_ev
    cons=_consensus_map(consensus)
    fin_comp=(financials or {}).get('companies',{})
    macro_score=((macro or {}).get('framework') or {}).get('macro_score')
    macro_score=50 if macro_score is None else macro_score
    rows=[]
    for s in stocks:
        code=s['code']; inds=ind_by_code.get(code,[])
        market_score=s.get('score') or 0
        # Flow component is made explicit so the dashboard can show confluence without hiding it in technical score.
        flow_strength=round(clamp(50+(s.get('foreign_ratio_pct') or 0)*4+(s.get('institution_ratio_pct') or 0)*4 + (6 if (s.get('foreign_5d') or 0)>0 else -4) + (6 if (s.get('institution_5d') or 0)>0 else -4)))
        news_score,news_items,news_count=_source_score(news_ev,code,inds)
        tel_score,tel_items,tel_count=_source_score(tel_ev,code,inds)
        rep_score,rep_items,rep_count=_source_score(rep_ev,code,inds)
        fund_score,fund_detail=_fund_score(fin_comp.get(code,[]))
        con_score,con_detail=_cons_score(cons.get(code))
        industry_score=round(fmean([ind_score[x] for x in inds])) if inds else None
        sources={
            'market':{'score':market_score,'available':True,'confidence':0.95},
            'flow':{'score':flow_strength,'available':True,'confidence':0.95},
            'news':{'score':news_score,'available':news_score is not None,'confidence':0.72,'count':news_count},
            'telegram':{'score':tel_score,'available':tel_score is not None,'confidence':0.52,'count':tel_count},
            'research':{'score':rep_score,'available':rep_score is not None,'confidence':0.82,'count':rep_count},
            'fundamental':{'score':fund_score,'available':fund_score is not None,'confidence':0.98,'detail':fund_detail},
            'consensus':{'score':con_score,'available':con_score is not None,'confidence':0.90,'detail':con_detail},
            'industry':{'score':industry_score,'available':industry_score is not None,'confidence':0.80},
        }
        weights={'market':0.23,'flow':0.12,'news':0.12,'telegram':0.07,'research':0.13,'fundamental':0.13,'consensus':0.10,'industry':0.10}
        avail=[k for k,v in sources.items() if v['available']]
        denom=sum(weights[k] for k in avail) or 1
        strength=sum((sources[k]['score'] or 0)*weights[k] for k in avail)/denom
        active=[k for k in avail if (sources[k]['score'] or 0)>=62]
        confluence=len(active)
        confluence_score=min(100,confluence/6*100)
        persistence=50
        persistence += 12 if (s.get('value_accel') or 0)>=1.2 else -6 if (s.get('value_accel') or 0)<0.8 else 0
        persistence += 10 if (s.get('foreign_5d') or 0)>0 else -6
        persistence += 10 if (s.get('institution_5d') or 0)>0 else -6
        repeat=min(3,news_count)+min(3,tel_count)+min(3,rep_count)
        persistence += min(18,repeat*3)
        persistence=clamp(persistence)
        confidence=100*sum(weights[k]*sources[k]['confidence'] for k in avail)/denom
        # Macro is a modest regime modifier, not a thesis replacement.
        macro_mod=(macro_score-50)*0.10
        integrated=clamp(0.62*strength+0.18*confluence_score+0.12*persistence+0.08*confidence+macro_mod)
        veto=[]
        if not s.get('above60'): veto.append('60일선 하회')
        if (s.get('foreign_5d') or 0)<0 and (s.get('institution_5d') or 0)<0: veto.append('외인·기관 5D 동반 순매도')
        if macro_score<40: veto.append('매크로 Risk-off')
        if len(avail)<4: veto.append('근거원 부족')
        if market_score>=75 and confluence<2: veto.append('가격/거래대금 단독 신호')
        score=round(integrated - min(12,len(veto)*2))
        if score>=82 and confluence>=4: grade='PRIME'
        elif score>=72 and confluence>=3: grade='WATCH'
        elif score>=62: grade='EARLY'
        else: grade='LOW'
        evidence=[]
        for e in news_items+tel_items+rep_items:
            evidence.append({'source':e['source'],'type':e['type'],'title':e['title'],'url':e.get('url'),'pqc':e.get('pqc',[]),'score':e['event_score'],'polarity':e['polarity']})
        rows.append({'code':code,'name':s['name'],'market':s.get('market'),'price':s.get('price'),'integrated_score':score,'grade':grade,
                     'strength':round(strength),'confluence_count':confluence,'active_sources':active,'persistence':round(persistence),'confidence':round(confidence),
                     'macro_score':macro_score,'veto':veto,'industries':inds,'components':sources,'evidence':evidence[:12],
                     'market_score':market_score,'total_value':s.get('total_value'),'day_pct':s.get('day_pct'),'week_pct':s.get('week_pct')})
    rows.sort(key=lambda x:(x['integrated_score'],x['confluence_count'],x.get('total_value') or 0),reverse=True)
    return {'status':'OK','method':'strength + confluence + persistence + confidence + macro modifier - veto','rows':rows,
            'events':all_events[:300], 'source_counts':{'news':len(news_ev),'telegram':len(tel_ev),'research':len(rep_ev)}}
