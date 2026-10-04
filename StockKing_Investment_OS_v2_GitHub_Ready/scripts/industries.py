from __future__ import annotations
from statistics import fmean

MAP={
 '반도체 장비':{'codes':['031980','403870','039030','084370','240810','095610'],'keywords':['반도체 장비','전공정 장비','후공정 장비','HBM 장비','etch','deposition'],'p':'AI/HBM CAPEX·장비 ASP','q':'발주량·웨이퍼 투입·가동률','c':'부품·납기·인건비','thesis':'수주/납기와 고객 CAPEX가 Q 선행지표. 장비 ASP와 믹스 개선을 P로 검증.'},
 'PCB/기판':{'codes':['222800','007660','353200'],'keywords':['PCB','기판','MLB','ABF','FC-BGA','CCL','800G','1.6T'],'p':'고다층·고사양 ASP','q':'AI 서버·네트워크·가속기 수요','c':'동박·CCL·수율','thesis':'AI 네트워크/서버 고사양화가 P×Q를 동시에 밀어주는지 확인.'},
 '테스트 인터페이스':{'codes':['095340','131290'],'keywords':['테스트 소켓','프로브카드','test socket','probe card','인터페이스'],'p':'핀수·복잡도 ASP','q':'GPU/HBM 테스트 시간·수량','c':'정밀가공·수율','thesis':'테스트 복잡도 상승과 고객 증설이 Q를 확대하는 구조인지 확인.'},
 '반도체 소재':{'codes':['064760','357780'],'keywords':['반도체 소재','포토레지스트','특수가스','고순도 소재'],'p':'고순도 소재 단가','q':'웨이퍼 투입량·가동률','c':'원재료·유틸리티','thesis':'메모리/파운드리 가동률 회복이 Q로 이어지는지 확인.'},
 'AI PCB':{'codes':['007660'],'keywords':['AI PCB','고다층 MLB','네트워크 보드','스위치 보드','가속기 보드'],'p':'고다층 MLB ASP','q':'스위치·가속기·네트워크 보드 수량','c':'CCL·동박·수율','thesis':'800G/1.6T 네트워크와 AI 가속기 채택 확대가 핵심.'}
}

def build_industries(stocks):
    sm={s['code']:s for s in stocks}; out=[]
    for name,cfg in MAP.items():
        arr=[sm[c] for c in cfg['codes'] if c in sm]
        if not arr: continue
        strength=round(fmean([s.get('score',0) for s in arr]))
        out.append({'name':name,'strength':strength,'p':cfg['p'],'q':cfg['q'],'c':cfg['c'],'thesis':cfg['thesis'],'members':[s['code'] for s in arr]})
    return sorted(out,key=lambda x:x['strength'],reverse=True)
