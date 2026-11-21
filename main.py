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
    count = 0
    for i in range(m):
        for j in range(m):
            acc += data0[i][j] * data1[i][j]
            count += 1
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
    print("#"+"-"*30)
    print("#[1] 필터 입력")
    print("#"+"-"*30)
    print("필터 A", f"{n}줄 입력, 공백 구분")
    f_a = input_matrix()
    print("필터 B", f"{n}줄 입력, 공백 구분")
    f_b = input_matrix()
    print()

    print("#"+"-"*30)
    print("#[2] 패턴 입력")
    print("#"+"-"*30)
    print("패턴", f"{n}줄 입력, 공백 구분")
    pattern = input_matrix()
    print()

    #판정 결과
    print("#"+"-"*30)
    print("#[3] MAC 결과")
    print("#"+"-"*30)
    start = time.time()
    print("A 점수:", end=" ")
    A_score = mac(f_a, pattern)
    print(A_score)
    print("B 점수:", end=" ")
    B_score = mac(f_b, pattern)
    print(B_score)
    finish = time.time()

 
    if abs(A_score - B_score) < 0.000000009:
        print("판정 불가 (|A-B| < 1e-9)")
    elif A_score > B_score:
        print("연산 시간:", f"{finish - start:.3f}", "초")
        print("판정: A")
    else:
        print("연산 시간:", f"{finish - start:.3f}", "초")
        print("판정: B")



elif choice == "2":
    a = ["size_5", "size_13", "size_25"]
    b = [["size_5_1", "size_5_2"], ["size_13_1", "size_13_2"], ["size_25_1", "size_25_2"]]
    calculating_time = [[0]*2 for _ in range(3)]

    print("#"+"-"*30)
    print("#[1] 필터 로드")
    print("#"+"-"*30)
    print()
    
    print("#"+"-"*30)
    print("#[2] 패턴 분석 (라벨 정규화 적용)")
    print("#"+"-"*30)
    for i in range(3):
        for j in range(2):
            print(f"---{(b[i][j])}---")
            start = time.time()
            print("Cross 점수:", end=" ")
            cross_score = mac(data0["filters"][a[i]]["cross"], data0["patterns"][b[i][j]]["input"])
            print(cross_score)
            print("  X   점수:", end=" ")
            x_score = mac(data0["filters"][a[i]]["x"], data0["patterns"][b[i][j]]["input"])
            print(x_score)
            finish = time.time()
            calculating_time[i][j] = finish - start
            print("시간:", f"{calculating_time[i][j]:.6f}", "초")
            if abs(cross_score - x_score) < 0.000000009:
                print("판정: UNDECIDED | FAIL (동점 규칙)")
            elif cross_score > x_score:
                print("판정: Cross | PASS")
            else:
                print("판정: X | PASS")
    print()
    
    print("#"+"-"*30)
    print("#[3] 성능 분석")
    print("#"+"-"*30)
    print("크기 | 평균시간(ms) | 연산 횟수")
    print("-"*20)
    category = ["5", "13", "25"]
    for i in range(3):
        print(category[i]+"x"+category[i], end=" ")
        print(f"{(calculating_time[i][0] + calculating_time[i][1])/2:.3f}", end=" ")
        print(int(category[i])**2)




