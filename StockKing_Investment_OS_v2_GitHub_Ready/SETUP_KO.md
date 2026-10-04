# 10분 설치 체크리스트

1. GitHub에서 새 저장소(예: `stockking-investment-os`) 생성
2. 이 ZIP의 **내용 전체**를 저장소 루트에 업로드
3. Settings → Pages → Source: **GitHub Actions**
4. Open DART API Key가 있으면 Settings → Secrets and variables → Actions → New repository secret
   - Name: `DART_API_KEY`
   - Value: 본인 인증키
5. `config/telegram_sources.csv`에 추적할 공개 Telegram 채널을 등록
6. 직접 받은 증권사 PDF는 `inputs/reports/`에 업로드
7. Actions → `Auto update StockKing Integrated Signal OS` → Run workflow → `full`
8. Actions가 끝나면 Pages 주소 접속

## 화면 첫 탭에서 볼 것

- **Integrated score**: 전체 신호 강도
- **Confluence**: 강한 독립 신호 개수
- **Persistence**: 거래대금/수급/이벤트 반복성
- **Confidence**: 확보된 출처의 신뢰도
- **Veto**: 추가 확인이 필요한 반대 신호
- **근거 보기**: 뉴스/Telegram/리포트 원문 링크와 P/Q/C 태그

## 주의

- GitHub Actions 예약실행은 플랫폼 사정상 몇 분 지연될 수 있습니다.
- KRX/네이버/Telegram 공개 페이지 구조가 바뀌면 해당 소스만 PENDING이 될 수 있도록 fail-soft로 설계했습니다.
- 실시간 틱/호가/프로그램 매매는 현재 공급원 미연결입니다. 장마감 확정 데이터가 핵심입니다.
