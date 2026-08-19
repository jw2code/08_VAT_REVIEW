import sqlite3
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 터미널이 출력하지 못하는 이모지나 특수문자같은걸 만났을때 대체 문자로 변경처리해서 에러를 방지
sys.stdout.reconfigure(errors="replace")

# transformers 실행시 발생하는 경고메시지등을 관리는 로깅
from transformers import logging as hf_logging

# 청킹하는 문자가 최대토큰ㄴ갯수를 넘어설때 지저분하게발생하는 에러 권고사항을 꺼줌
# 중요한 에러 문구는 그대로 출력 처리

hf_logging.set_verbosity_error()

from transformers import AutoTokenizer

from app.config import DB_PATH, EMBED_TOKENIZER

con = sqlite3.connect(DB_PATH)
con.execute("PRAGMA foreign_keys = ON")

tok = AutoTokenizer.from_pretrained()

# 텍스트를 인자로 전달받아서 모델이 이해하는 토큰으로 나누고 토큰의 갯수를 반환하는 함수
def ntok(text):
    return to


# 여러개의 문장을 토큰화 했을때 최소, 중간, 최대 토큰갯수를 파악하는 함수
def dist(values):
    return (f"최소 {min(values)}/중앙{int(statistics.median(values))}/최대{max(values)}")
    

if __name__ == "__main__" :
    details = [
        "짧은 상품 설명",
        "조금 더 긴 상품 설명입니다.",
        "아주 길고 자세한 상품 설명입니다...",
        "간단한 설명",
        "보통 길이의 상품 설명입니다."
    ]

token_counts = [ntok(detail) for detail in details]
print(token_counts)

dist(token_counts)
print(dist(token_counts))

# 현재 상품정보 데이터에서 지금 ai처리할때 수용되는 데이터의 퍼센트
# 작업순서 먼저 모든 상품의 토큰 수 확인(full_token),
# 그리고 최대 토큰을 넘어서지 않는 글의 데이터를 찾아 평균값 구함

fits = [min(n, EMBED_MAX_TOKENS) / n for n in full_tokens]

# n for n in full_tokens 각 상품 설명의 토큰수를 하나씩 확인
# 모델에 들어가는 토큰수 / 전체 토큰수
print(fits)

pritn(f" 임베딩 모델 상한 : {EMBED_MAX_TOKENS}토큰 ({EMBED_TOKENIZER})")
print(f" 상세 토큰 분포 : {dist(full_tokens)}")
print(f" 상한초과 : {len(over)/len(full_tokens)}건 {len(over)/len(full_tokens) * 100 :.0f}%")
print(f" 평균수용률 : {sum(fits)/len(fits)*100:.0f}%")

print("--------------------------------")

text = "안녕하세요. 반갑습니다."

print(tok.tokenizer(text))
