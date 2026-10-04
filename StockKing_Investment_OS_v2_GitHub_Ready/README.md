# StockKing Investment OS v2 — Integrated Signal Engine

사용자가 지속적으로 수행하는 **뉴스 · 텔레그램 · 거래대금 이상징후 · 마감시황 · 증권사 리포트 분석**을 종목/산업 단위로 합치는 자동 업데이트 대시보드입니다.

## 핵심 설계

각 종목은 다음 8개 레이어를 갖습니다.

1. **Market / Anomaly** — KRX+NXT 거래대금, 20/60일 z-score·백분위, 가속도, 회전율, CLV, 추세
2. **Flow** — 외국인·기관 당일 및 3/5일 지속성
3. **News Edge** — 쇼티지·병목·가격인상·CAPEX·수주·신사업·정책·리비전
4. **Telegram** — 등록한 공개 채널 메시지를 동일한 사건 분류기에 투입
5. **Research** — 네이버 리서치 + `inputs/reports/*.pdf` 사용자 PDF
6. **Fundamental** — Open DART 최근 8분기, YoY 매출/영업이익·OPM 변화
7. **12MF Revision** — 라이선스/수동 어댑터의 매출·OP·EPS·목표가 리비전
8. **Industry P×Q−C** — 산업 강도와 P/Q/C 드라이버

최종 점수는 **Strength + Confluence + Persistence + Confidence + Macro modifier − Veto**입니다. 이 점수는 자동 매수 신호가 아니라 조사 우선순위입니다.

## 자동 갱신 (KST)

- 08:20: 밤사이 뉴스·텔레그램·리포트·매크로
- 09:05 / 11:05 / 13:05 / 15:05: 경량 시장 재계산
- 16:45: 장마감 전체 갱신 (시장 + DART + 뉴스 + 텔레그램 + 리포트 + 매크로)
- 18:30: 저녁 뉴스·텔레그램·리포트 재수집
- 20:20: KRX 투자자 최종/NXT 애프터마켓 반영 최종 시장 갱신

> `pykrx` 기반 KRX 데이터는 **공식 장마감/확정 데이터 중심**입니다. 위 장중 스케줄은 새 데이터가 공개되면 재계산하는 구조이며, 증권사 WebSocket 같은 진짜 틱/실시간 데이터는 포함하지 않습니다. 진짜 장중 2시간 스캔이 필요하면 별도의 실시간 시세 공급원 어댑터를 연결해야 합니다.

## 입력/연결

### DART
GitHub Repository → Settings → Secrets and variables → Actions → `DART_API_KEY` 등록.

### Telegram
`config/telegram_sources.csv`에 공개 채널 username을 등록합니다.

```csv
channel,label
some_public_channel,반도체 채널
```

공개 `t.me/s/<channel>` preview를 읽으며, 접근/HTML 구조 변경 시 PENDING으로 실패 처리합니다.

### 직접 받은 증권사 PDF
`inputs/reports/`에 PDF를 넣습니다. 다음 full/sources 갱신 때 `USER PDF` 소스로 읽어 네이버 리서치와 함께 통합합니다.

### 12MF 컨센서스
공개 공식 API가 아닌 경우가 많아 `config/consensus.csv`를 공급원 어댑터 인터페이스로 사용합니다. 리비전율 열이 입력되면 통합점수에 반영됩니다.

## D0 추적

통합점수 **72 이상 + 독립 신호 3개 이상**을 D0로 기록하고 D+1/+3/+5/+10/+20 수익률을 자동 채웁니다. 향후 소스 조합별 승률/기대수익을 백테스트할 수 있습니다.

## 배포

1. 저장소에 전체 프로젝트 업로드
2. GitHub Pages → Source를 **GitHub Actions**로 설정
3. Actions의 `Auto update StockKing Integrated Signal OS`를 한 번 수동 실행
4. 이후 예약 실행이 `data/dashboard.json` / `data/data.js`를 갱신하고 Pages가 자동 재배포

## 데이터 원칙

- 없는 데이터는 만들지 않고 `PENDING`
- Telegram은 신뢰도 가중치를 낮게 적용
- DART/KRX 등 1차 원천은 높은 신뢰도 적용
- 뉴스/텔레그램/리포트는 종목 직접 언급과 산업 간접 노출을 구분
- 매크로는 개별 종목 논리를 뒤집는 신호가 아니라 제한적인 modifier
