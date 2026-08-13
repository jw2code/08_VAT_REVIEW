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
        print(value)

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