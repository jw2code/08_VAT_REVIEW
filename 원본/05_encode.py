from sentence_transformers import SentenceTransformer

model = SentenceTransformer("intfloat/multilingual-e5-small")

# encode 가 하는 일이 전부다 — 글자를 넣으면 숫자 묶음이 나온다
v = model.encode("건조한 피부에 순한 토너")

# type(v) 는 "v 가 어떤 종류의 값인가" 를 알려준다.
# 그냥 찍으면 <class 'numpy.ndarray'> 처럼 길게 나오는데,
# 뒤에 .__name__ 을 붙이면 종류의 "이름만" 꺼내준다 -> ndarray
#
# 앞뒤로 밑줄 두 개가 붙은 이름들(__name__ · __len__ 등)은 파이썬이 미리 정해둔
# 특별한 이름이다. 우리가 지은 게 아니라 파이썬이 자동으로 채워둔 값이라고 보면 된다
print("타입:", type(v).__name__)

# shape 는 "몇 개짜리인가" 를 알려준다. (384,) = 384개가 한 줄로 들어 있다
print("모양:", v.shape)

# 앞의 다섯 개만 찍어본다. round 는 소수점을 잘라 보기 좋게 만든다
print("앞 5개:", v[:5].round(4))
