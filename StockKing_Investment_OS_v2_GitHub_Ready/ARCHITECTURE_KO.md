# StockKing v2 통합 시그널 아키텍처

## 데이터 흐름

뉴스 / Telegram / Naver Research / USER PDF
→ Entity Mapping(종목·산업)
→ Event Classification(쇼티지·가격·CAPEX·수주·리비전·신사업·정책)
→ P/Q/C 태깅
→ KRX/NXT 가격·거래대금·외국인·기관 결합
→ DART 8분기 / 12MF Revision 결합
→ Strength / Confluence / Persistence / Confidence
→ Macro modifier / Veto
→ Integrated Score
→ 마감시황 / D0 신호 / D+1·3·5·10·20 추적

## 가중치

- Market/Anomaly 23%
- Flow 12%
- News 12%
- Telegram 7%
- Research 13%
- Fundamental 13%
- Consensus Revision 10%
- Industry P×Q−C 10%

가용한 데이터 소스만으로 가중치를 재정규화합니다. 데이터가 없으면 0점 처리하지 않고 PENDING으로 제외합니다.

## 최종 점수

`0.62 × Strength + 0.18 × Confluence + 0.12 × Persistence + 0.08 × Confidence + Macro modifier - Veto penalty`

- PRIME: 82점 이상 + 강한 독립 신호 4개 이상
- WATCH: 72점 이상 + 강한 독립 신호 3개 이상
- EARLY: 62점 이상
- LOW: 그 미만

등급은 매수추천이 아니라 조사 우선순위입니다.

## Telegram 처리

- 공개 채널 preview 수집
- 동일/유사 재전송 텍스트는 SHA 기반으로 중복 제거
- 재전송 수는 attention 정보로만 보존
- 텔레그램 자체 신뢰도는 낮게 설정
- 원문/공시/IR/뉴스와 결합될수록 Confluence가 증가

## Veto

- 60일선 하회
- 외국인·기관 5일 동반 순매도
- 매크로 Risk-off
- 근거원 부족
- 가격/거래대금 단독 신호

Veto는 자동 제외가 아니라 사람이 다시 확인해야 하는 반대 신호입니다.
