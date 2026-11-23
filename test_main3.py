"""MAC(Multiply-Accumulate) 기반 Cross / X 패턴 판정기.

사용하는 라이브러리는 json, time 두 개뿐이다.
(math, fractions, re, unicodedata, collections 등은 사용하지 않는다.)

모드 1: 3x3 필터 A/B와 패턴을 직접 입력해 MAC 점수를 비교한다.
모드 2: data.json의 필터·패턴을 일괄 판정하고, 실패 케이스의 원인을
        "데이터/스키마", "로직", "수치 비교" 세 분류로 진단한다.
"""

import json
import time

FILENAME = "data.json"
EPSILON = 1e-9      # 동점 판정 허용 오차 (절대/상대 공용)
REPEAT = 200        # 시간 측정 반복 횟수
USER_N = 3          # 모드 1의 행렬 크기
INF = float("inf")

LABEL_MAP = {
    "+": "cross",
    "cross": "cross",
    "plus": "cross",
    "x": "x",
    "×": "x",
}

CATEGORY_TITLES = {
    "SCHEMA": "데이터/스키마 문제",
    "LOGIC": "로직 문제",
    "NUMERIC": "수치 비교 문제",
}


class SchemaError(Exception):
    """데이터/스키마 문제 (계산 이전 단계의 입력 오류)."""


# ---------------------------------------------------------------------------
# 표준 라이브러리 없이 직접 구현한 도우미
# ---------------------------------------------------------------------------
def is_finite(x):
    """NaN(자기 자신과 다름)과 ±inf를 걸러낸다. (math.isfinite 대체)"""
    return x == x and x != INF and x != -INF


def is_tie(a, b):
    """절대/상대 오차 모두 허용. (math.isclose 대체)"""
    return abs(a - b) <= max(EPSILON * max(abs(a), abs(b)), EPSILON)


def to_halfwidth(text):
    """전각 문자(＋, Ｘ, 전각 공백)를 반각으로 변환. (unicodedata 대체)"""
    out = []
    for ch in text:
        code = ord(ch)
        if code == 0x3000:
            out.append(" ")
        elif 0xFF01 <= code <= 0xFF5E:
            out.append(chr(code - 0xFEE0))
        else:
            out.append(ch)
    return "".join(out)


def natural_key(s):
    """'size_5' < 'size_13' 이 되도록 숫자 덩어리를 정수로 비교. (re 대체)"""
    parts = []
    buf = ""
    for ch in s:
        if buf and buf[-1].isdigit() != ch.isdigit():
            parts.append((0, int(buf)) if buf.isdigit() else (1, buf))
            buf = ""
        buf += ch
    if buf:
        parts.append((0, int(buf)) if buf.isdigit() else (1, buf))
    return parts


def to_decimal(v):
    """수를 (정수 가수 m, 10의 지수 e)로 오차 없이 분해한다: v = m × 10**e.

    float는 repr() 문자열(예: '1.0000000001', '1e-07')을 십진수로 읽는다.
    (fractions.Fraction 대체)
    """
    if isinstance(v, int):
        return v, 0
    s = repr(v).lower()
    exp = 0
    if "e" in s:
        s, e = s.split("e")
        exp = int(e)
    sign = -1 if s.startswith("-") else 1
    s = s.lstrip("+-")
    if "." in s:
        whole, frac = s.split(".")
        exp -= len(frac)
        s = whole + frac
    return sign * int(s), exp


def mac_exact(filt, pattern):
    """오차 없는 MAC 점수를 (정수, 10의 지수) 쌍으로 반환한다."""
    n = len(filt)
    terms = []
    for i in range(n):
        for j in range(n):
            m1, e1 = to_decimal(filt[i][j])
            m2, e2 = to_decimal(pattern[i][j])
            if m1 != 0 and m2 != 0:
                terms.append((m1 * m2, e1 + e2))
    if not terms:
        return 0, 0
    base = min(e for _, e in terms)
    return sum(m * 10 ** (e - base) for m, e in terms), base


def compare_exact(a, b):
    """(정수, 지수) 쌍 두 개를 정확히 비교: a>b → 1, 같음 → 0, a<b → -1."""
    (m1, e1), (m2, e2) = a, b
    base = min(e1, e2)
    x = m1 * 10 ** (e1 - base)
    y = m2 * 10 ** (e2 - base)
    return (x > y) - (x < y)


# ---------------------------------------------------------------------------
# 데이터 로드 / 검증
# ---------------------------------------------------------------------------
def load_data(filename=FILENAME):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise SchemaError(f"파일을 찾을 수 없습니다: {filename}")
    except json.JSONDecodeError as e:
        raise SchemaError(f"JSON 형식이 손상되었습니다: {e}")


def get_path(d, *keys):
    """중첩 dict에서 키 경로를 따라가며, 없으면 SchemaError를 올린다."""
    cur = d
    walked = []
    for k in keys:
        walked.append(str(k))
        if not isinstance(cur, dict) or k not in cur:
            raise SchemaError(f"키 없음: {'/'.join(walked)}")
        cur = cur[k]
    return cur


def validate_matrix(m, name):
    if not isinstance(m, list) or not m:
        raise SchemaError(f"{name}: 비어 있거나 리스트가 아님")
    n = len(m)
    for r in m:
        if not isinstance(r, list) or len(r) != n:
            raise SchemaError(f"{name}: {n}x{n} 정사각 행렬이 아님")
        for v in r:
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise SchemaError(f"{name}: 숫자가 아닌 값 {v!r}")


def normalize_label(label):
    key = to_halfwidth(str(label)).strip().lower()
    if key not in LABEL_MAP:
        raise ValueError(f"알 수 없는 라벨: {label!r}")
    return LABEL_MAP[key]


# ---------------------------------------------------------------------------
# MAC 연산 / 판정
# ---------------------------------------------------------------------------
def mac(filt, pattern):
    n = len(filt)
    if n != len(pattern) or any(len(r) != n for r in filt) or any(len(r) != n for r in pattern):
        raise ValueError("필터와 패턴의 크기가 다릅니다.")
    return sum(filt[i][j] * pattern[i][j] for i in range(n) for j in range(n))


def decide(cross_score, x_score, tie):
    if tie:
        return None
    return "cross" if cross_score > x_score else "x"


def measure(fn, repeat=REPEAT):
    """fn을 repeat회 실행한 평균 시간(초)."""
    start = time.perf_counter()
    for _ in range(repeat):
        fn()
    return (time.perf_counter() - start) / repeat


# ---------------------------------------------------------------------------
# 케이스 진단 (실패 원인 3분류)
# ---------------------------------------------------------------------------
def analyze_case(data, name):
    result = {"name": name, "ok": False, "category": None, "reason": "",
              "cross": None, "x": None, "predicted": None, "expected": None,
              "size": None, "time": None}

    def fail(category, reason):
        result.update(ok=False, category=category, reason=reason)
        return result

    # ① 데이터/스키마 검증
    try:
        pat = get_path(data, "patterns", name, "input")
        expected = normalize_label(get_path(data, "patterns", name, "expected"))
        validate_matrix(pat, f"{name}/input")
        size = len(pat)
        flt = get_path(data, "filters", f"size_{size}")
        cross_f = get_path(flt, "cross")
        x_f = get_path(flt, "x")
        for m, nm in ((cross_f, "cross"), (x_f, "x")):
            validate_matrix(m, f"size_{size}/{nm}")
            if len(m) != size:
                raise SchemaError(f"size_{size}/{nm}: 패턴 크기({size})와 불일치")
    except (SchemaError, ValueError) as e:
        return fail("SCHEMA", str(e))

    result.update(expected=expected, size=size)

    # 계산 + 시간 측정 (Cross, X 두 번의 MAC을 1회로 본다)
    cs, xs = mac(cross_f, pat), mac(x_f, pat)
    result.update(cross=cs, x=xs)
    result["time"] = measure(lambda: (mac(cross_f, pat), mac(x_f, pat)))

    # ② 수치 이상값 (NaN / inf)
    if not (is_finite(cs) and is_finite(xs)):
        return fail("NUMERIC", f"비정상 점수 (cross={cs}, x={xs})")

    # ③ float 판정 vs 정확 계산 판정
    predicted = decide(cs, xs, is_tie(cs, xs))
    c = compare_exact(mac_exact(cross_f, pat), mac_exact(x_f, pat))
    exact = None if c == 0 else ("cross" if c > 0 else "x")
    result["predicted"] = predicted

    if predicted == expected:
        result.update(ok=True)
        return result
    if predicted != exact:
        return fail("NUMERIC",
                    f"float 판정={predicted}, 정확 계산={exact} "
                    f"(EPSILON={EPSILON}, cross={cs}, x={xs})")
    if predicted is None:
        return fail("LOGIC", f"정확히 동점: 필터가 구분하지 못함 (cross={cs}, x={xs})")
    return fail("LOGIC",
                f"판정 {predicted} ≠ 기대 {expected} "
                f"(정확 계산도 동일 → 필터 키/라벨/규칙 확인)")


# ---------------------------------------------------------------------------
# 출력 도우미
# ---------------------------------------------------------------------------
def header(title):
    print("#" + "-" * 30)
    print(f"#{title}")
    print("#" + "-" * 30)


def print_case(r):
    print(f"---{r['name']}---")
    if r["cross"] is not None:
        print("Cross 점수:", r["cross"])
        print("  X   점수:", r["x"])
    if r["ok"]:
        print(f"판정: {r['predicted']} | expected: {r['expected']} | PASS")
    else:
        if r["cross"] is None:
            label = "N/A (계산 전 실패)"
        else:
            label = r["predicted"] if r["predicted"] is not None else "UNDECIDED"
        exp = r["expected"] if r["expected"] is not None else "?"
        print(f"판정: {label} | expected: {exp} | FAIL [{CATEGORY_TITLES[r['category']]}]")


def print_performance(results):
    header("[3] 성능 분석")
    by_size = {}
    for r in results:
        if r["time"] is not None:
            by_size.setdefault(r["size"], []).append(r["time"])
    print("크기 | 평균시간(ms) | 연산 횟수(곱셈)")
    print("-" * 32)
    for size in sorted(by_size):
        avg_ms = sum(by_size[size]) / len(by_size[size]) * 1000
        print(f"{size}x{size} | {avg_ms:.4f} | {2 * size * size}")
    print(f"(패턴 1개 = Cross + X 두 번의 MAC, {REPEAT}회 반복 평균)")
    print()


def print_summary(results):
    header("[4] 결과 요약")
    passed = sum(1 for r in results if r["ok"])
    failed = len(results) - passed
    print(f"총 테스트: {len(results)}개")
    print(f"통과: {passed}개")
    print(f"실패: {failed}개")
    print()

    groups = {}
    for r in results:
        if not r["ok"]:
            groups.setdefault(r["category"], []).append(r)

    print("실패 케이스:")
    if not groups:
        print(" 없음")
        return
    for cat in ("SCHEMA", "LOGIC", "NUMERIC"):
        if cat in groups:
            print(f" [{CATEGORY_TITLES[cat]}] {len(groups[cat])}건")
            for r in groups[cat]:
                print(f"   - {r['name']}: {r['reason']}")


# ---------------------------------------------------------------------------
# 모드 1: 사용자 입력
# ---------------------------------------------------------------------------
def input_matrix(n=USER_N):
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


def run_user_mode():
    n = USER_N
    header("[1] 필터 입력")
    print("필터 A", f"{n}줄 입력, 공백 구분")
    f_a = input_matrix(n)
    print("필터 B", f"{n}줄 입력, 공백 구분")
    f_b = input_matrix(n)
    print()

    header("[2] 패턴 입력")
    print("패턴", f"{n}줄 입력, 공백 구분")
    pattern = input_matrix(n)
    print()

    header("[3] MAC 결과")
    a_score = mac(f_a, pattern)
    b_score = mac(f_b, pattern)
    elapsed = measure(lambda: (mac(f_a, pattern), mac(f_b, pattern)))
    print("A 점수:", a_score)
    print("B 점수:", b_score)
    print("연산 시간:", f"{elapsed * 1000:.4f}", "ms", f"({REPEAT}회 반복 평균)")

    if is_tie(a_score, b_score):
        print(f"판정 불가 (|A-B| < {EPSILON})")
    elif a_score > b_score:
        print("판정: A")
    else:
        print("판정: B")


# ---------------------------------------------------------------------------
# 모드 2: data.json 분석
# ---------------------------------------------------------------------------
def run_json_mode():
    header("[1] 필터 로드")
    try:
        data = load_data(FILENAME)
        filters = get_path(data, "filters")
        names = sorted(get_path(data, "patterns"), key=natural_key)
        if not isinstance(filters, dict):
            raise SchemaError("filters가 객체(dict)가 아님")
    except SchemaError as e:
        print(f"X 데이터 오류: {e}")
        return

    for size_key in sorted(filters, key=natural_key):
        try:
            for kind in ("cross", "x"):
                validate_matrix(get_path(filters, size_key, kind), f"{size_key}/{kind}")
            print(f"V {size_key} 필터 로드 완료 (Cross, X)")
        except SchemaError as e:
            print(f"X {size_key} 필터 오류: {e}")
    print()

    header("[2] 패턴 분석 (라벨 정규화 + 원인 진단)")
    results = []
    for name in names:
        r = analyze_case(data, name)
        print_case(r)
        results.append(r)
    print()

    print_performance(results)
    print_summary(results)

# ---------------------------------------------------------------------------
# 메인 프로그램
# ---------------------------------------------------------------------------

def main():
    print("""
1. 사용자 입력 (3x3)
2. data.json 분석
""")
    choice = input("선택:").strip()
    if choice == "1":
        run_user_mode()
    elif choice == "2":
        run_json_mode()
    else:
        print("1 또는 2를 입력하세요.")


if __name__ == "__main__":
    main()
