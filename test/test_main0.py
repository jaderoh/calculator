import json
import time

FILENAME = "data.json"

Epsilon = 1e-9

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

#data0 = load_data(FILENAME)

"""
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

def mac(filt, pattern):
    n = len(filt)
    if n != len(pattern) or any(len(r) != n for r in filt) or any(len(r) != n for r in pattern):
        raise ValueError("필터와 패턴의 크기가 다릅니다.")
    return sum(filt[i][j] * pattern[i][j] for i in range(n) for j in range(n)) # MAC 연산

#print(mac(data0["filters"]["size_5"]["cross"],data0["filters"]["size_5"]["x"]))
"""
def input_matrix():
    #n = int(input("행렬 크기: "))
    n = 3
    matrix = [list(map(int, input().split())) for _ in range(n)]
    print("입력된 행렬\n", matrix)
    return matrix
"""
def input_matrix():
    n = 3
    while True:
        try:
            rows = []
            for k in range(n):
                row = list(map(int, input().split()))
                if len(row) != n:
                    raise ValueError(f"{k + 1}번째 줄: 정수 {n}개가 필요합니다 (입력 {len(row)}개)")
                rows.append(row)
            print("입력된 행렬\n", rows)
            return rows
        except ValueError as e:
            print(f"입력 오류: {e}")
            print(f"정수 {n}개를 공백으로 구분해 {n}줄을 처음부터 다시 입력하세요.")

LABEL_MAP = {
    "+": "cross",
    "cross": "cross",
    "plus": "cross",
    "x": "x",
    "×": "x",
}

def normalize_label(label):
    key = str(label).strip().lower()
    if key not in LABEL_MAP:
        raise ValueError(f"알 수 없는 라벨: {label!r}")
    return LABEL_MAP[key]

#print(normalize_label("+"))        # cross
#print(normalize_label(" Plus "))   # cross
#print(normalize_label("X"))        # x


def choice1():
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
    A_score = mac(f_a, pattern)
    B_score = mac(f_b, pattern)
    finish = time.time()
    print("A 점수:", end=" ")
    print(A_score)
    print("B 점수:", end=" ")
    print(B_score)
 
    if abs(A_score - B_score) < Epsilon:
        print("판정 불가 (|A-B| < 1e-9)")
    elif A_score > B_score:
        print("연산 시간:", f"{(finish - start)*1000:.3f}", "ms")
        print("판정: A")
    else:
        print("연산 시간:", f"{(finish - start)*1000:.3f}", "ms")
        print("판정: B")

def choice2():
    a = ["size_5", "size_13", "size_25"]
    b = [["size_5_1", "size_5_2"], ["size_13_1", "size_13_2"], ["size_25_1", "size_25_2"]]
    calculating_time = [[0]*2 for _ in range(3)]

    print("#"+"-"*30)
    print("#[1] 필터 로드")
    print("#"+"-"*30)
    data0 = load_data(FILENAME)
    for i in range(3):
        print(f"V {a[i]} 필터 로드 완료 (Cross, X)")
    print()
    
    print("#"+"-"*30)
    print("#[2] 패턴 분석 (라벨 정규화 적용)")
    print("#"+"-"*30)
    count_pass = 0
    count_fail = 0
    failures = []   # 루프 시작 전에 선언 (마지막 "실패 케이스" 출력용)

    for i in range(3):
        for j in range(2):
            print(f"---{(b[i][j])}---")
            start = time.time()
            cross_score = mac(data0["filters"][a[i]]["cross"], data0["patterns"][b[i][j]]["input"])
            x_score = mac(data0["filters"][a[i]]["x"], data0["patterns"][b[i][j]]["input"])
            finish = time.time()
            calculating_time[i][j] = finish - start
            print("Cross 점수:", end=" ")
            print(cross_score)
            print("  X   점수:", end=" ")
            print(x_score)

            #print("시간:", f"{(calculating_time[i][j]*1000):.3f}", "ms")
            
            # ... 점수 계산 후 ...
            pattern_name = b[i][j]
            raw_expected = data0["patterns"][pattern_name]["expected"]

            # 1) 판정 결과 결정
            if abs(cross_score - x_score) < Epsilon:
                predicted = None
            elif cross_score > x_score:
                predicted = "cross"
            else:
                predicted = "x"

            # 2) 기대 라벨 정규화 + 비교
            try:
                expected = normalize_label(raw_expected)
            except ValueError as e:
                print(f"판정: FAIL ({e})")
                failures.append(f"{pattern_name}: {e}")
                count_fail += 1
                continue

            if predicted is None:
                print(f"판정: UNDECIDED | expected: {expected} | FAIL (동점 규칙)")
                failures.append(f"{pattern_name}: 동점 (cross={cross_score}, x={x_score})")
                count_fail += 1
            elif predicted == expected:
                print(f"판정: {predicted} | expected: {expected} | PASS")
                count_pass += 1
            else:
                print(f"판정: {predicted} | expected: {expected} | FAIL")
                failures.append(f"{pattern_name}: 판정 {predicted}, 기대 {expected}")
                count_fail += 1
    print()
    
    print("#"+"-"*30)
    print("#[3] 성능 분석")
    print("#"+"-"*30)
    print("크기 | 평균시간(ms) | 연산 횟수")
    print("-"*20)
    category = ["5", "13", "25"]
    for i in range(3):
        print(category[i]+"x"+category[i], end=" ")
        print(f"{((calculating_time[i][0] + calculating_time[i][1])/2)*1000:.3f}", end=" ")
        print(int(category[i])**2)
    print()

    print("#"+"-"*30)
    print("#[4] 결과 요약")
    print("#"+"-"*30)
    count_total = count_pass + count_fail
    print(f"총 테스트: {count_total}개")
    print(f"통과: {count_pass}개")
    print(f"실패: {count_fail}개")
    print()
    print("실패 케이스:")
    if failures:
        for f in failures:
            print(" -", f)
    else:
        print(" 없음")

def main():
    print(
    """
    1. 사용자 입력 (3x3)
    2. data.json 분석
    """
    )
    choice = input("선택:")
    if choice == "1":
        choice1()
    elif choice == "2":
        choice2()

if __name__ == "__main__":
    main()