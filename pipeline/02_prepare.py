import sqlite3
import statistics     # 통계치 만들어주는 모듈
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 터미널이 출력하지 못하는 이모지나 특수문자 등을 만날 때 대체 문자로 변경처리하여 에러 방지
sys.stdout.reconfigure(errors="replace")

from app.db import query

# transformers 실행 시 발생하는 경고 메시지 등을 관리하는 로깅처리 모듈
from transformers import logging as hf_logging

# 청킹하는 문자가 최대 토큰 갯수를 넘어설 때 지저분하게 발생하는 에러 권고사항을 꺼줌
# 중요한 에러 문구는 그대로 출력 처리
hf_logging.set_verbosity_error()

from langchain_text_splitters import MarkdownHeaderTextSplitter

from transformers import AutoTokenizer

from app.config import DB_PATH, EMBED_TOKENIZER, EMBED_MAX_TOKENS

con = sqlite3.connect(DB_PATH)
con.execute("PRAGMA foreign_keys = ON")

tok = AutoTokenizer.from_pretrained(EMBED_TOKENIZER)

# 텍스트 인자로 전달받아서 모델이 이해하는 토큰으로 나누고 토큰의 갯수를 반환하는 함수
def ntok(text):
    return len(tok.encode(text))

# 여러개의 문장을 토큰화 했을 때 최소, 중간, 최대 토큰갯수를 파악하는 함수
def dist(values):
    return(f"최소 {min(values)} / 중앙 {int(statistics.median(values))} / 최대 {max(values)}")


CHUNK_SIZE = 384
CHUNK_OVERLAP = 48
PREFIX_BUDGET = 32  # 접두사 [상품명 > 위치] 본문내용
RESPLIT_OVER = EMBED_MAX_TOKENS - PREFIX_BUDGET
HEADERS = [("##", "section")] # 청킹할 데이터의 표시 경계 구분점 생성 (markdown)
SEPERATORS = ["\n\n", "\n", "다", "요", ".", ",", ""]

# Document(
#    page_content = "수분을 공급하는 크림입니다"
#    metadata = {"section" : "제품소개"}
#)

# 지금부터는 글자 수가 아니라 "## 주의사항" 같은 md의 제목을 경계로 문자를 자름 (청킹)
md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS)


if __name__ == "__main__":
    details = query("""
        SELECT product_details.product_id, products.name, product_details.detail
        FROM product_details JOIN products ON product_details.product_id = products.product_id
        ORDER BY product_details.product_id
    """)

# 글에서 ## 제품소개, ## 주요성분 같은 2단계제목을 발견할 때마다 본문을 분리해서 저장할 빈 리스트생정
sections = []

for pid, pname, detail in details :
    for doc in md_splitter.split_text(detail):
        text = doc.page_content.strip() # 앞뒤 공백이 제거된 md 제목기준으로 나눈 본문 덩어리

        if not text :
            continue

        sections.append((pid, pname, doc.metadata.get("section","(머릿말)"), text))
        # (제품아이디, 제품이름, 마크다운 제목, 제목에 해당하는 본문내용)

print(sections[0][2])
print("-------")
print(sections[0][3])



    """
    full_tokens = [ntok(detail) for _, _, detail in details]
    #print("full_tokens", full_tokens)
    #print()
    
    # 현재 제품 설명중에서 최대 토큰인 512 토큰을 넘어가는 글의 토큰수만 다시 리스트로 분류
    over = [ n for n in full_tokens if n > EMBED_MAX_TOKENS ]
    
    # 현재 상품정보 데이터에서 지금 ai처리할 때 수용되는 데이터의 퍼센트
    # 작업순서 먼저 모든 상품의 토큰 수 확인 (full_token),
    # 그리고 최대 토큰을 넘어서지 않는 글의 데이터를 찾아 평균값을 구함
    less = [ n for n in full_tokens if n < EMBED_MAX_TOKENS ]
    
    fits = [min(n, EMBED_MAX_TOKENS) / n for n in full_tokens]
    
    # n for n in full_tokens 각 상품설명의 토큰수를 하나씩 확인
    # 모델에 들어가는 토큰 수
      
    # print(fits)  
    
    print(f"    임베딩 모델 상한: {EMBED_MAX_TOKENS}토큰 ({EMBED_TOKENIZER})")
    print(f"    상세 토큰 분포 : {dist(full_tokens)}")
    print(f"    상한초과 : {len(over)/len(full_tokens)}건 {len(over)/len(full_tokens) * 100 :.0f}%")
    print(f"    평균수용률 : {sum(fits)/len(fits)*100:.0f}%")
    
    print("==============")
    
    avg = sum(fits) / len(fits)
    print(f"평균 {avg:.1f}")
    
    print(f" {(len(less) / len(full_tokens)) * 100} %")
    
    #print(over)
    #print(len(over))
    
    ## 일정 토큰 용량이 넘어간 경우 정보가 유출되는것으로 볼 수 있으므로 보안처리 해야함 (?)
    
    
    #print(details)
    #print(len(details))
    
    #details = [
    #    ('P001', "상품명1", "상품1의 엄청 긴 설명"),
    #]
    
    #details = [
    #    "짧은 상품 설명",
    #    "조금 더 긴 상품 설명입니다",
    #    "아주 길고 자세한 상품 설명입니다...",
    #    "간단한 설명"
    #    "보통 길이의 상품설명입니다"
    #]
    
    #token_counts = [ntok(detail) for detail in details]
    #print(token_counts)

    #print(dist(token_counts))
    
    # dist로 반환받은 중앙값은 평균값이 아님
    # 왜 우리는 토큰 검사를 할 때 평균값이 아닌 중앙값을 고려해야 되는지 고민
    # 텍스트들의 토큰 갯수를 고려할 때 평균값을 쓰면 안되는 이유는 특정 글 하나가 엄청 긴 텍스트일때
    # 그 유별한 길이의 텍스트 정보때문에 평균값의 수치가 오염될 수 있음
    # 그래서 실제 임베딩시에는 평균값이 아닌 사용자가 일반적으로 많이 쓰는 중앙값을 활용해야 함
    
    # 미션 - DB에서 query 함수로 실제 특정 고객의 리뷰를 모두 가져와서 각 후기의 토큰 값 계산하고 중앙값 출력
    
    
    print("========================================")
    
    text = "안녕하세요. 반갑습니다. "
    print(tok.tokenize(text))
    # ['▁안녕하세요', '.', '▁반', '갑', '습니다', '.'] << 단어에따라 토큰이 다름. 학습이 안된건 오체분시함
    
    text1 = "안녕하세요"
    text2 = "메틸데이트"
    print("안녕하세요", tok.tokenize(text1))
    print("메틸데이트", tok.tokenize(text2))
    # 안녕하세요 ['▁안녕하세요'] , 메틸데이트 ['▁메', '틸', '데이', '트']
    # 앞에 붙은 언더바는 랭체인이 자기혼자 일하면서 붙인 일종의 손잡이(?) 종종 붙어나옴
    """
