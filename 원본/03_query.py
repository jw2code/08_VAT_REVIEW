import sqlite3

con = sqlite3.connect("shop.db")     # 아까 만든 파일을 연다
cur = con.cursor()

# SELECT  꺼낼 칸 이름들 (별표 * 를 쓰면 전부)
# FROM    어느 표에서
# WHERE   어떤 조건인 줄만
#
# execute 는 명령을 보내기만 한다. 결과를 받으려면 아래 둘 중 하나를 붙여야 한다 ─
#   fetchone()  첫 줄 하나만    -> ('C001', '박은수', 53, ...)
#   fetchall()  걸린 줄 전부    -> [(...), (...), ...]
print(cur.execute("""
    SELECT customer_id, name, age, skin_type, city
    FROM customers
    WHERE customer_id = 'C001'
""").fetchone())

# 두 표를 붙이면 같은 이름의 칸이 양쪽에 있을 수 있다 (여기서는 name 이 둘 다 있다).
# 그래서 "어느 표의 칸인지" 를 표 이름을 앞에 붙여 밝힌다 — products.name 처럼.
# 헷갈릴 일이 없으면 생략해도 되지만, 붙여두는 편이 읽기 쉽다
rows = cur.execute("""
    SELECT purchases.purchased_at, products.name, products.price, purchases.rating, purchases.is_holdout
    FROM purchases
    JOIN products ON purchases.product_id = products.product_id   -- 두 표에서 번호가 같은 줄끼리 붙인다
    WHERE purchases.customer_id = 'C007'
    ORDER BY purchases.purchased_at                          -- 날짜 오름차순 (오래된 것부터)
""").fetchall()                                      # 걸린 줄 전부를 목록으로 받는다

for r in rows:      # r 은 줄 하나. ('2025-09-16', '병풀 링클 클렌징오일', 28100, 3, 0)
    print(r)

# GROUP BY 는 같은 값끼리 한 덩어리로 묶는다. 묶고 나면 덩어리마다 하나씩 계산할 수 있다 ─
#   COUNT(*)   그 덩어리에 줄이 몇 개인가        (* 는 "줄 자체를 센다")
#   AVG(칸)    그 칸의 평균
#   ROUND(값, 2)  소수점 둘째 자리까지 반올림
# AS 는 계산 결과에 이름을 붙이는 것이다. 이름이 있어야 아래 ORDER BY 에서 가리킬 수 있다
for r in cur.execute("""
    SELECT products.name, COUNT(*) AS n_sold, ROUND(AVG(purchases.rating), 2) AS avg_rating
    FROM purchases
    JOIN products ON purchases.product_id = products.product_id
    GROUP BY products.product_id          -- 상품별로 묶는다
    ORDER BY n_sold DESC           -- DESC = 큰 것부터 (ASC 는 작은 것부터, 안 적으면 ASC)
    LIMIT 5                        -- 위에서 다섯 줄만
""").fetchall():
    print(r)

# fetchone() 은 줄 하나를 묶음으로 준다. 칸이 하나뿐이어도 (80,) 처럼 온다.
# 숫자만 필요하면 뒤에 [0] 을 붙여 첫 칸을 꺼낸다
print(cur.execute("SELECT COUNT(*) FROM products WHERE price <= 30000").fetchone())

# AND 는 두 조건을 모두 만족하는 줄만 남긴다 (하나만 만족해도 되면 OR)
# LIKE 는 글자가 들어 있는지 보는 것이고, % 는 "여기에 아무 글자나 와도 된다" 는 뜻이다.
#   '%선물용%'  ->  앞뒤에 뭐가 붙든 선물용 이라는 글자가 들어 있으면 걸린다
for r in cur.execute("""
    SELECT name, brand, price FROM products
    WHERE price <= 30000 AND tags LIKE '%선물용%'
    ORDER BY price DESC
    LIMIT 5
""").fetchall():
    print(r)
    # [0] 을 붙인 이유는 위에서 본 그대로다 — (1500,) 에서 숫자만 꺼낸다
print("전체", cur.execute("SELECT COUNT(*) FROM purchases").fetchone()[0])
print("숨김", cur.execute("SELECT COUNT(*) FROM purchases WHERE is_holdout = 1").fetchone()[0])
print("이력", cur.execute("SELECT COUNT(*) FROM purchases WHERE is_holdout = 0").fetchone()[0])

# 앞으로 이력을 꺼낼 때는 항상 이 조건을 붙인다.
#
# 여기서 물음표가 또 나왔다. 값을 글자로 이어붙이지 않고 물음표 자리에 넘기는 방식이다.
# execute 의 두 번째 자리에 값 묶음을 준다 —  ("C007",)
# 쉼표가 붙은 이유는, 값이 하나일 때 ("C007") 이라고 쓰면 파이썬이 그냥 글자로 보기 때문이다.
# 쉼표를 찍어야 "값이 하나 든 묶음"이 된다
rows = cur.execute("""
    SELECT products.name, products.category, products.price, purchases.rating, purchases.review
    FROM purchases
    JOIN products ON purchases.product_id = products.product_id
    WHERE purchases.customer_id = ?
      AND purchases.is_holdout = 0        -- 정답은 빼고 가져온다
    ORDER BY purchases.purchased_at
""", ("C007",)).fetchall()


# 후기에 010- 이 들어 있는 줄을 세 개만 꺼내본다
for r in cur.execute("SELECT customer_id, review FROM purchases WHERE review LIKE '%010-%' LIMIT 3").fetchall():
    print(r)

# 하이픈 없이 010 만 들어 있는 것까지 세면 몇 건인가
print(cur.execute("SELECT COUNT(*) FROM purchases WHERE review LIKE '%010%'").fetchone()[0])



