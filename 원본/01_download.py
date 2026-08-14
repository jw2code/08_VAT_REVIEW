# 실습에 쓸 데이터를 인터넷에서 받아온다.
# urllib 은 파이썬에 기본으로 들어 있는 인터넷 도구다. 설치할 것이 없다
import urllib.request

# Path 는 폴더와 파일 경로를 다루는 도구다. 이것도 기본으로 들어 있다
from pathlib import Path

# raw.githubusercontent.com 은 깃허브에 올라간 파일의 "날것"을 주는 주소다.
# 브라우저용 꾸밈 없이 파일 내용만 그대로 온다
base = "https://raw.githubusercontent.com/tubi55/dcodelab-class-data/main/"

# data 라는 폴더를 만든다. exist_ok=True 는 "이미 있으면 그냥 넘어가라"는 뜻이다.
# 이게 없으면 두 번째 실행할 때 에러가 난다
Path("data").mkdir(exist_ok=True)

for name in ["customers.csv", "products.csv", "purchases.csv"]:
    # urlretrieve 는 주소의 파일을 그대로 받아 저장한다.
    # 앞이 받아올 주소, 뒤가 저장할 자리다
    urllib.request.urlretrieve(base + name, f"data/{name}")
    print("받음:", name)
