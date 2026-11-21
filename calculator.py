# 외국어학습지방 인증 2026년 11월 21일(토) 캐서린

import json
import time

FILENAME = "data.json"

def load_data(FILENAME):
    try:
        with open(FILENAME, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        return []
    except (json.JSONDecodeError, KeyError, TypeError):
        print("저장 파일이 손상되어 빈 목록으로 시작합니다.")
        return []

    with open(FILENAME, "R", encoding="utf-8") as f:
        data = json.load(f)
    return data

data0 = load_data(FILENAME)

def mac(data0, data1):
    m = 3
    acc = 0
    for i in range(m):
        for j in range(m):
            acc += data0[i][j] * data1[i][j]
    return acc
"""
def pad(data, pad_size):
    m = len(data)
    p = pad_size
    re_data = [[0]*(m+p*2)]*(m+p*2)
    for i in range(m):
        for j in range(m):
            re_data[p+i][p+j] = data[i][j]
    return re_data
"""

#print(pad(data1, 3))
#print(mac(data0["filters"]["size_5"]["cross"],data0["filters"]["size_5"]["x"]))

def input_matrix():
    #n = int(input("행렬 크기: "))
    n = 3
    matrix = [list(map(int, input().split())) for _ in range(n)]
    print("입력된 행렬\n", matrix)
    return matrix

print(
"""
1. 사용자 입력 (3x3)
2. data.json 분석
"""
)
choice = input("선택:")
if choice == "1":
    n = 3
    print("[1] 필터 입력")
    print("필터 A", n, "줄 입력, 공백 구분")
    f_a = input_matrix()
    print("필터 B", n, "줄 입력, 공백 구분")
    f_b = input_matrix()
    print("[2] 패턴 입력")
    print("패턴", n, "줄 입력, 공백 구분")
    pattern = input_matrix()

    start = time.time()
    print("A 점수:", end=" ")
    A_score = mac(f_a, pattern)
    print(A_score)
    print()
    print("B 점수:", end=" ")
    B_score = mac(f_b, pattern)
    print(B_score)
    finish = time.time()
    print("연산 시간:", finish - start, "초")

    if abs(A_score - B_score) < 0.000000009:
        print("판정 불가")
    elif A_score > B_score:
        print("판정: A")
    else:
        print("판정: B")


