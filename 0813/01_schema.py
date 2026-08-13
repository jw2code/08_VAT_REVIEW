# github에 내 작업을 단계별로 올리는 방법
# 1. 깃허브에서 내가 올리고싶은 작업의 전용 저장소 URL복사(private)
# 2. 내 ㅈ가업폴더에 터미널 열고 다음 명령어 차례대로 실행
# git init
# git remote add origin 저장소 url
# 3. 단계별로 기록을 남기고 싶을때마다 파일 저장 
#    -> git add . -> git commit -m "커밋메세지" -> git push origin --all
import re
#정규표현식 검사해주는 파이썬 전용 패키지

import csv
from pathlib import Path

# 폴더 구조가 중첩되어 있기 때문에 루트 경로를 변수에 저장
ROOT = Path(__file__).resolve().parent.parent
# 루트경로에서 data폴더가 있는 경로를 다시 변수에 저장
DATA_DIR = ROOT / "data"


# 인자로 csv파일이 있는 패스 경로를 전달하면 각 파일의 필드명만 리스트형태로 반환하는 함수
def read_csv(path):
    with open(path,encoding="utf-8",newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


# csv파일을 반복돌면서 read_csv함수 호출해서 각 파일당 필드데이터와 각 row 데이터정보를 출력
for path in sorted(DATA_DIR.glob("*.csv")):
    columns, rows = read_csv(path)
    # 실제 각 csv 파일의 필드명, 필드값 확인   
    for column in columns :
        value = rows[0][column]


# 해당 값이 정수인지 확인하는 함수
def looks_int(text):
    body = text[1:] if text.startswith("-") else text
    if not body.isdigit():
        #정수가아님
        print("정수가 아님")
        return False
    # 만약에 정수일때 앞자리가 0으로 시작하면 전화번호 (조건 2자리 이상일 때)
    print("전화번호임")
    return not (len(body)) > 1 and body.startswith("0") 

# 소수 판별 함수
def looks_float(text) :
        # float 실수반환되는지 우선확인
    try :
        float(text)

    # 위의 모든 경우가 아닌 실수가 아닌게 확실하니 False반환
    except ValueError :
        return False

    # 전달값에 .이 없으면 실수일리가 없음
    if "." not in text :
        return False
    
    # 위의 모든 예외사항 통과하면 얘는 무조건 실수
    return True

print(looks_float("3"))

def looks_data(text):
    return re.fullmatch(r"\d{4}-\{2}-\d{2}",text)

# 타입 추론 함수 생성
def infer_type(values):
    seen = [v for v in values if v!=""]
    if not seen :
        return "TEXT"
    if all(looks_int(v) for v in seen) :
        return "INTEGER"
    if all(looks_float(v) for v in seen) :
        return "FLOAT"
    if all(looks_data(v) for v in seen) :
        return "DATE"

    return"TEXT"

# 모든 csv파일을 하나씩 검사해서 컬럼명과 각 행의 값의 타입을 분석
for path in sorted(DATA_DIR.glob("*.csv")) :
    columns, rows = read_csv(path)
    print(f"\n{path.stem} ({len(rows)})")
    for column in columns :
        kind = infer_type(r[column] for r in rows)

        # next(조건에 맞는 값, 디폴트값)->조건에 맞는 값이 반복되면 하나만 출력하고 건너뜀, 조건문으로 빈 문자열 출력 그렇게 건너뛴 값을 반환
        # 반복되는 필드명을 출력하고 싶을 때
        example = next((r[column] for r in rows if r[column] != ""),"")

        print(f"{column} : {kind}")

# Pk를 찾아주는 함수
def infer_pk(columns, rows) :
    for col in columns : 
        if not col.endsvith("_id") :
            continue

        values = [r[col] for r in rows]
        if "" in values :
            continue
        # value값이 중복되지 않으면 그건 PK
        if len(set(values)) == len(values) :
            return col

    # 위의 조건이 모두 만족하지 않는다면 PK가 없음
    return None




# 특정 PK의 주인 테이블 찾기
def owner_of(column, tables) :
    # 첫번째 인자로 들어온 PK에서 _id제거하고 그 뒤에 s, es붙여서
    # 두번째 인자로 들어온 테이블 리스트랑 매칭이 되는 이름을 찾음(해당 pK의 주인 테이블 명)
    stem = column[:-3]
    for candidate in (stem, stem+"s", stem+"es") :
        if candidate in tables :
            return candidate
        
    return None

# 1. 모든 테이블별 필드, 데이터타입, PK 구하기
tables = {}
for path in sorted(DATA_DIR.glob("*.csv")):
    colums, rows = read_csv(path)
    tables[path.stem] = {
        "columns" : columns,
        "rows" : rows,
        "type" : {col:infer_type([r.get(col) for r in rows]) for col in columns},
        "pk" : infer_pk(colums, rows)
    }
print(tables["customers"])


# 2. 특정 테이블에 연결되어 있는 외래키 찾기
for name, table in tables.item() : #표 이름과 내용을 그룹으로 꺼냄
    fks = []
    for col in tabgle["colsumns"] :
        if not col.endswith("_id"):
            continue
        owner = owner_of(col, tables)
        if not owner or owner == name :
            continue
        if tables[owner]["pk"] != col :
            continue
        fks.append((col,owner))

        table["fks"] = fks

        print(fks)

