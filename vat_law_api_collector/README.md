# VAT Review Agent 법률 데이터 수집기

법제처 국가법령정보 공동활용 API를 이용해 VAT 검토에 필요한 자료를 수집합니다.

## 수집 범위

- 현행법령: 부가가치세법, 시행령, 시행규칙의 본문
- 판례: VAT 관련 목록과 본문
- 조세심판원 특별행정심판재결례: VAT 관련 목록과 본문
- 법령해석례: VAT 관련 목록과 본문
- 국세청 법령해석: VAT 관련 목록

국세청 법령해석은 공식 API가 목록만 제공하므로 본문 대신 상세링크를 저장합니다.
판례 중 국세법령정보시스템 출처 문서가 JSON 본문을 제공하지 않으면 HTML 본문으로 자동 재시도합니다.

## 처음 한 번만 준비

Windows PowerShell 기준:

```powershell
cd "이 폴더를 압축 해제한 경로\vat_law_api_collector"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

`.env`에서 `LAW_API_OC=` 오른쪽에 본인의 승인된 API 인증값을 입력합니다. 인증값은 코드나 GitHub에 올리지 마세요.

## 전체 수집

```powershell
python vat_law_collector.py
```

기본 검색어는 `부가가치세`, `매입세액`, `세금계산서`입니다. 같은 문서가 여러 검색어에 걸려도 일련번호 기준으로 한 번만 저장합니다.

최근 자료만 수집하려면:

```powershell
python vat_law_collector.py --start-date 20150101 --end-date 20261231
```

특정 출처만 시험하려면:

```powershell
python vat_law_collector.py --sources laws
python vat_law_collector.py --sources precedents
python vat_law_collector.py --sources tax_tribunal
```

검색어를 추가하려면:

```powershell
python vat_law_collector.py --keywords 부가가치세 매입세액 세금계산서 공통매입세액 면세사업
```

## 결과 파일

`output` 폴더에 다음 파일이 생성됩니다.

- `laws.csv`: 현행 부가가치세 법령
- `precedents.csv`: 법원 판례
- `tax_tribunal.csv`: 조세심판례
- `interpretations.csv`: 법령해석례
- `nts.csv`: 국세청 법령해석 목록 및 상세링크
- `rag_documents.csv`: 위 자료를 하나로 합친 임베딩·검색용 파일
- `rag_chunks.csv`: 긴 문서를 약 3,500자 단위로 나눈 실제 임베딩 입력용 파일
- `collection_summary.csv`: 출처별 수집 건수와 본문 보유 건수
- `collection_errors.csv`: 실패한 페이지·문서와 오류 원인
- `raw/`: API 원본 JSON 및 판례 HTML 대체 원문

CSV는 한글 Excel에서 바로 열 수 있도록 `UTF-8 with BOM`으로 저장됩니다. 원본은 나중에 추출 컬럼을 바꾸거나 판정 로직을 검증할 때 필요하므로 삭제하지 않는 편이 좋습니다.

## 권장 첫 실행 순서

1. `python vat_law_collector.py --sources laws`로 인증값과 법령 API를 확인합니다.
2. `python vat_law_collector.py --sources tax_tribunal --start-date 20200101`로 소규모 수집을 시험합니다.
3. 결과 CSV의 사건명·세목·본문을 확인한 뒤 전체 수집을 실행합니다.

실행이 중간에 끊겨도 이미 받은 본문 원본은 다시 사용합니다. 목록은 최신 결과와 누락 여부를 확인하기 위해 다시 조회합니다.

## 공식 API 대상값

| 데이터 | 목록/본문 target | 본문 제공 |
|---|---|---|
| 현행법령(시행일) | `eflaw` | JSON |
| 판례 | `prec` | JSON, 일부 국세청 출처는 HTML |
| 조세심판원 특별행정심판재결례 | `ttSpecialDecc` | JSON |
| 법령해석례 | `expc` | JSON |
| 국세청 법령해석 | `ntsCgmExpc` | 공식 API는 목록만 제공 |
