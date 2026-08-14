# VAT Review Agent — SQLite·임베딩 실습 적용본

기존 01~08번 화장품 예제의 흐름을 유지하면서 VAT 전표·법령 규칙·정제 판례 데이터에 맞춘 버전입니다.

## 폴더 배치

```text
C:\jw_project\8jwlab
├─ 01_peek.py
├─ 02_load_db.py
├─ 03_query.py
├─ 04_embed_first.py
├─ 05_encode.py
├─ 06_compare.py
├─ 07_embed_precedents.py
├─ 08_search.py
└─ data
   ├─ precedents_usable.csv
   ├─ vat_rules.csv
   └─ vat_screening_results.csv
```

## 실행 순서

PowerShell에서 다음 순서대로 실행합니다.

```powershell
cd C:\jw_project\8jwlab
python 01_peek.py
python 02_load_db.py
python 03_query.py
python 04_embed_first.py
python 05_encode.py
python 06_compare.py
python 07_embed_precedents.py
python 08_search.py 18260102-1
```

직접 문장으로 검색할 수도 있습니다.

```powershell
python 08_search.py "대표이사 업무용 2,000cc 승용차 주유"
```

`02_load_db.py`를 실행하면 `vat_review.db`가 생성됩니다. `07_embed_precedents.py`는 최초 실행 때 임베딩 모델을 내려받고 정제 판례 531건의 벡터를 `precedent_vectors` 표에 저장합니다.

필요 패키지가 없다면 다음 명령으로 설치합니다.

```powershell
pip install sentence-transformers numpy
```
