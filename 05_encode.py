from sentence_transformers import SentenceTransformer

model = SentenceTransformer("intfloat/multilingual-e5-small")

# e5 모델은 검색 질문 앞에 query: 를 붙이면 검색용 문장이라는 뜻을 더 잘 이해한다.
v = model.encode("query: 대표이사 업무용 2,000cc 승용차 주유비의 매입세액 공제 여부")

# type(v) 는 "v 가 어떤 종류의 값인가" 를 알려준다.
# 그냥 찍으면 <class 'numpy.ndarray'> 처럼 길게 나오는데,
# 뒤에 .__name__ 을 붙이면 종류의 "이름만" 꺼내준다 -> ndarray
print("타입:", type(v).__name__)

# shape 는 "몇 개짜리인가" 를 알려준다. (384,) = 384개가 한 줄로 들어 있다.
print("모양:", v.shape)

# 앞의 다섯 개만 찍어본다. round 는 소수점을 잘라 보기 좋게 만든다.
print("앞 5개:", v[:5].round(4))
