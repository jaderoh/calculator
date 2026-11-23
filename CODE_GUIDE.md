# 코드 설명서 — 함수별 해설

MAC(Multiply-Accumulate) 연산으로 패턴이 Cross(`+`) 필터와 X 필터 중 어느 쪽에 더 가까운지 판정하는 프로그램의 함수별 설명서입니다. 사용하는 라이브러리는 `json`, `time` 두 개뿐입니다.

> 예시 값은 실제로 코드를 실행해서 확인한 결과입니다.

## 목차

1. [전체 구조](#1-전체-구조)
2. [상수와 예외](#2-상수와-예외)
3. [데이터 로드·검증 함수](#3-데이터-로드검증-함수)
4. [MAC 연산·판정 함수](#4-mac-연산판정-함수)
5. [직접 구현한 도우미 함수](#5-직접-구현한-도우미-함수)
6. [진단 함수 `analyze_case`](#6-진단-함수-analyze_case)
7. [모드 실행·출력 함수](#7-모드-실행출력-함수)
8. [참고: 코드 속 알아둘 점](#8-참고-코드-속-알아둘-점)

---

## 1. 전체 구조

### 프로그램 흐름

```
main()
 ├─ 선택 1 → choice1()   : 3x3 필터 A/B와 패턴을 직접 입력해 비교
 │            ├─ input_matrix() ×3
 │            ├─ mac() ×2, measure()
 │            └─ 판정 출력
 └─ 선택 2 → choice2()   : data.json 일괄 분석
              ├─ load_data()
              ├─ analyze_case() × 패턴 수
              │     ├─ get_path(), validate_matrix(), normalize_label()   ← 스키마 검증
              │     ├─ mac(), measure(), is_finite()                      ← 계산·수치 검사
              │     └─ decide(), is_tie(), mac_exact(), compare_exact()   ← 판정·정확 비교
              ├─ print_case()      (케이스별 출력)
              ├─ print_performance()
              └─ print_summary()
```

### 함수 한눈에 보기

| 분류 | 함수 | 한 줄 요약 |
|------|------|------------|
| 로드·검증 | `load_data` | JSON 파일을 읽어 반환 |
| | `get_path` | 중첩 dict에서 키 경로를 따라가며 값을 꺼냄 |
| | `validate_matrix` | 행렬이 정사각 숫자 리스트인지 검사 |
| | `normalize_label` | 라벨 표기를 `cross` / `x`로 통일 |
| MAC·판정 | `mac` | 필터와 패턴의 MAC 점수 계산 |
| | `decide` | 점수 비교로 `cross` / `x` / `None` 결정 |
| | `measure` | 함수를 반복 실행한 평균 시간 측정 |
| 도우미 | `is_finite` | NaN·inf 검사 |
| | `is_tie` | 두 점수가 사실상 같은지 판정 |
| | `to_halfwidth` | 전각 문자를 반각으로 변환 |
| | `natural_key` | `size_5` < `size_13` 정렬용 키 |
| | `to_decimal` | 수를 `(정수, 10의 지수)`로 정확히 분해 |
| | `mac_exact` | 오차 없는 MAC 점수 |
| | `compare_exact` | 오차 없는 점수 비교 |
| 진단 | `analyze_case` | 패턴 하나를 검증·계산·판정하고 실패 원인을 분류 |
| 실행·출력 | `input_matrix` | 3x3 행렬을 입력받음 (재입력 지원) |
| | `choice1` / `choice2` | 모드 1 / 모드 2 실행 |
| | `print_case` / `print_performance` / `print_summary` | 결과 출력 |
| | `main` | 메뉴 표시와 모드 선택 |

---

## 2. 상수와 예외

```python
FILENAME = "data.json"
EPSILON = 1e-9
INF = float("inf")
```

| 상수 | 의미 |
|------|------|
| `FILENAME` | 분석할 JSON 파일 이름 |
| `EPSILON` | 동점으로 볼 허용 오차 (`1e-9`) |
| `INF` | 무한대. `is_finite()`에서 사용 |

```python
CATEGORY_TITLES = {"SCHEMA": "데이터/스키마 문제", "LOGIC": "로직 문제", "NUMERIC": "수치 비교 문제"}
```

실패 분류 코드를 화면에 표시할 이름으로 바꾸는 사전입니다.

```python
class SchemaError(Exception):
    """데이터/스키마 문제 (계산 이전 단계의 입력 오류)."""
```

데이터 형식이 잘못됐을 때 올리는 전용 예외입니다. `analyze_case()`가 이 예외를 잡아 `SCHEMA` 실패로 기록합니다. 코드에서 `get_path`보다 아래에 정의돼 있지만, 예외는 함수가 **실행될 때** 찾으므로 문제가 없습니다.

---

## 3. 데이터 로드·검증 함수

### `load_data(FILENAME)`

JSON 파일을 읽어 파이썬 객체(dict)로 반환합니다.

| 상황 | 동작 |
|------|------|
| 정상 | 파싱한 데이터 반환 |
| 파일 없음 (`FileNotFoundError`) | "파일을 찾을 수 없습니다" 출력 후 `[]` 반환 |
| JSON 손상 (`JSONDecodeError`) | "저장 파일이 손상되어…" 출력 후 `[]` 반환 |

- 실패해도 예외를 던지지 않고 빈 리스트를 돌려주므로, **호출하는 쪽(`choice2`)이 반환값을 검사**해야 합니다.
- 매개변수 이름이 전역 상수와 같은 `FILENAME`이라서 함수 안에서는 인자로 받은 값이 쓰입니다.

### `get_path(d, *keys)`

중첩된 dict에서 키를 차례로 따라가 값을 꺼냅니다. 키가 없으면 `SchemaError`를 올립니다.

```python
get_path({"a": {"b": 1}}, "a", "b")   # 1
get_path({"a": {"b": 1}}, "a", "c")   # SchemaError: 키 없음: a/c
```

- `data["patterns"][name]["input"]`처럼 바로 접근하면 키가 없을 때 `KeyError`로 프로그램이 멈추지만, 이 함수는 **어느 경로에서 막혔는지** 메시지에 담아 줍니다.
- 중간 값이 dict가 아닌 경우도 같은 방식으로 처리합니다.

### `validate_matrix(m, name)`

`m`이 **비어 있지 않은 N×N 정사각 숫자 행렬**인지 검사합니다. 어긋나면 `name`을 넣은 메시지로 `SchemaError`를 올립니다.

| 입력 | 결과 |
|------|------|
| `[]` | `m: 비어 있거나 리스트가 아님` |
| `[[1, 2], [3]]` | `m: 2x2 정사각 행렬이 아님` |
| `[[1, "a"], [3, 4]]` | `m: 숫자가 아닌 값 'a'` |
| `[[True, 0], [0, 0]]` | `m: 숫자가 아닌 값 True` |

`isinstance(v, bool)`을 따로 검사하는 이유는 파이썬에서 `True`가 `int`의 하위 타입이라, 이 검사가 없으면 `True`가 숫자 1로 통과하기 때문입니다.

### `normalize_label(label)`

정답 라벨의 다양한 표기를 `"cross"` 또는 `"x"`로 통일합니다.

```
처리 순서: 문자열로 변환 → 전각을 반각으로(to_halfwidth) → 앞뒤 공백 제거 → 소문자로 → LABEL_MAP 조회
```

```python
normalize_label(" Plus ")   # "cross"
normalize_label("＋")        # "cross"   (전각 +)
normalize_label("×")        # "x"
normalize_label("zzz")      # ValueError: 알 수 없는 라벨: 'zzz'
```

`LABEL_MAP`에 없는 표기는 `ValueError`를 올립니다. 새 표기를 허용하려면 `LABEL_MAP`에 항목을 추가하면 됩니다.

---

## 4. MAC 연산·판정 함수

### `mac(filt, pattern)`

두 행렬의 같은 위치 원소를 곱해서 모두 더합니다. 프로그램의 핵심 연산입니다.

```
score = Σ filt[i][j] × pattern[i][j]
```

```python
cross = [[0,1,0],[1,1,1],[0,1,0]]
x     = [[1,0,1],[0,1,0],[1,0,1]]
mac(cross, cross)   # 5   (겹치는 칸이 5개)
mac(x, cross)       # 1   (가운데 한 칸만 겹침)
```

- 시작할 때 행렬 크기를 검사하고, 크기가 다르거나 정사각이 아니면 `ValueError("필터와 패턴의 크기가 다릅니다.")`를 올립니다.
- 크기를 `len(filt)`로 구하므로 3×3뿐 아니라 5×5, 13×13, 25×25에서도 동작합니다.
- 입력이 정수면 결과도 정수, 하나라도 float이면 결과는 float입니다.

### `decide(cross_score, x_score, tie)`

두 점수와 동점 여부를 받아 판정 결과를 돌려줍니다.

| 조건 | 반환값 |
|------|--------|
| `tie`가 `True` | `None` (판정 불가) |
| Cross 점수가 더 큼 | `"cross"` |
| 그 외 | `"x"` |

```python
decide(5, 1, False)   # "cross"
decide(1, 5, False)   # "x"
decide(3, 3, True)    # None
```

동점 판정은 이 함수 밖에서 `is_tie()`로 하고 결과(`tie`)만 넘겨받는 구조입니다.

### `measure(fn, repeat=20)`

`fn`을 `repeat`번 실행하고 **1회당 평균 시간(초)**을 반환합니다.

```python
elapsed = measure(lambda: (mac(f_a, pattern), mac(f_b, pattern)))
```

- `time.perf_counter()`는 시간 측정용으로 정밀도가 높은 시계입니다.
- 3×3 계산은 몇 마이크로초라서 1회 측정은 오차가 큽니다. 반복해서 평균을 내면 안정적입니다.
- 계산이 아니라 **"실행할 작업 자체"**를 넘겨야 하므로 `lambda`로 감싸서 전달합니다. `lambda: (...)`는 이름 없는 작은 함수이며, `measure` 안의 `fn()`이 호출될 때 비로소 실행됩니다.

---

## 5. 직접 구현한 도우미 함수

`math`, `fractions`, `unicodedata`, `re`를 쓰지 않기 위해 직접 만든 함수들입니다.

### `is_finite(x)`

`x`가 유한한 수인지 검사합니다. NaN과 ±inf를 걸러냅니다.

```python
return x == x and x != INF and x != -INF
```

NaN은 **자기 자신과도 같지 않다**(`nan == nan`이 `False`)는 성질을 이용한 것이 `x == x`입니다.

```python
is_finite(3)                 # True
is_finite(float("nan"))      # False
is_finite(float("inf"))      # False
```

### `is_tie(a, b)`

두 점수가 사실상 같은지 판정합니다. **절대 오차와 상대 오차를 모두** 허용합니다.

```python
abs(a - b) <= max(EPSILON * max(abs(a), abs(b)), EPSILON)
```

| 호출 | 결과 | 이유 |
|------|------|------|
| `is_tie(1, 1.0000000001)` | `True` | 차이 1e-10 이 `EPSILON`(1e-9) 이내 |
| `is_tie(1, 1.1)` | `False` | 차이가 큼 |
| `is_tie(0.1 + 0.2, 0.3)` | `True` | 부동소수점 오차(약 5e-17)는 무시 |

값이 매우 클 때는 상대 오차 항이, 0 근처일 때는 절대 오차 항이 기준이 됩니다.

### `to_halfwidth(text)`

전각 문자를 반각으로 바꿉니다.

| 범위 | 처리 |
|------|------|
| 전각 공백 (U+3000) | 일반 공백 `" "` |
| 전각 `！`~`～` (U+FF01~U+FF5E) | 코드값에서 `0xFEE0`을 빼서 반각으로 |
| 그 외 | 그대로 |

```python
to_halfwidth("＋Ｘ　ａ")   # '+X a'
```

### `natural_key(s)`

문자열 정렬 키를 만들어, `size_5`, `size_13`, `size_25`가 **숫자 크기 순서**로 정렬되게 합니다. 일반 문자열 정렬은 `size_13`이 `size_5`보다 앞에 오기 때문입니다.

```python
natural_key("size_13")   # [(1, 'size_'), (0, 13)]
sorted(["size_25", "size_5", "size_13"], key=natural_key)
# ['size_5', 'size_13', 'size_25']
```

숫자 덩어리는 `(0, 정수)`, 문자 덩어리는 `(1, 문자열)` 튜플로 만듭니다. 이렇게 하면 정수와 문자열을 직접 비교하다 생기는 `TypeError`를 피할 수 있습니다.

### `to_decimal(v)`

수 `v`를 `(정수 가수 m, 10의 지수 e)`로 **오차 없이** 분해합니다. `v = m × 10**e`입니다.

```python
to_decimal(5)               # (5, 0)
to_decimal(0.1)             # (1, -1)            = 1 × 10⁻¹
to_decimal(1e-07)           # (1, -7)
to_decimal(-1.5e+20)        # (-15, 19)
to_decimal(1.0000000001)    # (10000000001, -10)
```

- 정수는 그대로 반환합니다.
- float는 `repr()`이 만든 **십진 문자열**(예: `'1.0000000001'`, `'1e-07'`)을 읽습니다. 이진 부동소수점 내부 표현이 아니라 사람이 보는 십진 표기를 그대로 정수로 바꾸므로 반올림 오차가 없습니다.
- `int`, `float`만 지원하고, 그 외 타입은 `validate_matrix()`가 먼저 걸러냅니다.

### `mac_exact(filt, pattern)`

`mac()`과 같은 계산을 **정수 연산만으로** 수행해서, 오차 없는 점수를 `(정수, 10의 지수)` 쌍으로 반환합니다.

1. 각 항 `filt[i][j] × pattern[i][j]`를 `to_decimal`로 분해해 가수끼리 곱하고 지수끼리 더합니다.
2. 곱이 0인 항은 건너뜁니다.
3. 가장 작은 지수(`base`)에 맞춰 `m × 10**(e - base)`를 정수로 모두 더합니다.

```python
mac_exact([[0.1, 0.2], [0, 0]], [[1, 1], [0, 0]])   # (3, -1)  → 3 × 10⁻¹ = 0.3
mac_exact([[0, 0], [0, 0]], [[1, 1], [1, 1]])       # (0, 0)
```

파이썬의 `int`는 크기 제한이 없어 이 과정에 반올림이 생기지 않습니다.

### `compare_exact(a, b)`

`(정수, 지수)` 쌍 두 개를 정확히 비교합니다. 지수를 작은 쪽에 맞춰 정수로 만든 뒤 비교합니다.

| 결과 | 의미 |
|------|------|
| `1` | `a > b` |
| `0` | `a == b` |
| `-1` | `a < b` |

```python
compare_exact((3, -1), (30, -2))              # 0   (0.3 == 0.30)
compare_exact((3, -1), (4, -1))               # -1  (0.3 < 0.4)
compare_exact((1, 0), (10000000001, -10))     # -1  (1 < 1.0000000001)
```

---

## 6. 진단 함수 `analyze_case`

### `analyze_case(data, name)`

패턴 하나를 검증, 계산, 판정하고 **결과 딕셔너리**를 반환합니다. 실패하면 원인을 3분류 중 하나로 기록합니다. 한 케이스의 문제가 전체를 멈추게 하지 않고, 항상 결과를 돌려줍니다.

### 반환 딕셔너리

| 키 | 의미 |
|----|------|
| `name` | 패턴 이름 |
| `ok` | 통과 여부 |
| `category` | 실패 분류 (`SCHEMA` / `LOGIC` / `NUMERIC` / `None`) |
| `reason` | 실패 이유 메시지 |
| `cross`, `x` | Cross 점수, X 점수 |
| `predicted` | 프로그램의 판정 (`"cross"` / `"x"` / `None`) |
| `expected` | 정규화된 정답 라벨 |
| `size` | 패턴 크기 N |
| `time` | Cross + X 계산 평균 시간(초) |

### 처리 단계

```
(1) 데이터/스키마 검증
    patterns/<name>/input, expected 읽기 → 행렬 검증 → size_<N> 필터 찾기 → 필터 검증·크기 일치
    └ 하나라도 어긋나면 → SCHEMA 실패 (계산 전에 종료)

계산 + 시간 측정
    cs = mac(cross_f, pat), xs = mac(x_f, pat), time = measure(...)

(2) 수치 이상값 검사
    cs 또는 xs가 NaN/inf → NUMERIC 실패

(3) float 판정 vs 정확 계산 판정
    predicted = decide(cs, xs, is_tie(cs, xs))
    exact     = compare_exact(mac_exact(...), mac_exact(...)) 로 얻은 정확한 판정
    ├ predicted == expected              → 통과 (ok = True)
    ├ predicted != exact                 → NUMERIC (float 오차나 EPSILON 때문에 판정이 달라짐)
    ├ predicted is None (정확히도 동점)  → LOGIC (필터가 구분하지 못함)
    └ 그 외                              → LOGIC (정확히 계산해도 기대 라벨과 다름)
```

### 세 분류의 의미

| 분류 | 의미 | 대표 원인 | 확인할 곳 |
|------|------|-----------|-----------|
| `SCHEMA` | 입력이 계산 가능한 형태가 아님 | 키 누락, 정사각 아님, 숫자 아님, 크기 불일치, 알 수 없는 라벨 | `data.json`, `LABEL_MAP` |
| `NUMERIC` | 수치 비교 때문에 판정이 뒤집힘 | NaN/inf, 점수 차이가 `EPSILON`보다 작아 동점 처리 | `EPSILON`, 자료형 |
| `LOGIC` | 정확히 계산해도 결과가 기대와 다름 | 필터 키 뒤바뀜, 정답 라벨 오기입, 필터가 두 패턴을 구분 못함 | 필터·라벨 데이터, 판정 규칙 |

**③의 핵심**은 같은 계산을 오차 없이 한 번 더 해서 비교하는 것입니다. float 판정과 정확 판정이 **다르면** 부동소수점·`EPSILON` 문제(`NUMERIC`)이고, **같은데도** 정답과 다르면 데이터나 규칙 문제(`LOGIC`)입니다.

### 예시

| 상황 | 분류 | 메시지 예 |
|------|------|-----------|
| `size_7` 필터가 없음 | `SCHEMA` | `키 없음: filters/size_7` |
| 점수 차이가 1e-10 (cross=1, x=1.0000000001) | `NUMERIC` | `float 판정=None, 정확 계산=x (EPSILON=1e-09, ...)` |
| 기대 라벨을 일부러 틀리게 적음 | `LOGIC` | `판정 x ≠ 기대 cross (정확 계산도 동일 → ...)` |

---

## 7. 모드 실행·출력 함수

### `input_matrix()`

3줄을 입력받아 3×3 정수 행렬을 반환합니다.

- 한 줄을 `input().split()`으로 나눠 `int`로 변환합니다.
- 줄마다 정수가 3개인지 검사하고, 아니면 `ValueError`를 올립니다.
- 숫자가 아닌 값이 있어 `int()`가 실패해도 같은 `except`에서 잡힙니다.
- 오류가 나면 안내 후 **처음부터 다시 입력**을 받습니다 (`while True`).
- 성공하면 입력된 행렬을 출력하고 반환합니다.

### `choice1()` — 모드 1: 사용자 입력

1. 필터 A, 필터 B, 패턴을 `input_matrix()`로 각각 입력받습니다.
2. `mac()`으로 `A_score`, `B_score`를 계산합니다.
3. `measure()`로 두 계산의 평균 시간을 잽니다.
4. 판정을 출력합니다.

| 조건 | 출력 |
|------|------|
| `abs(A - B) < EPSILON` | `판정 불가` (연산 시간은 출력하지 않음) |
| `A_score > B_score` | 연산 시간 + `판정: A` |
| 그 외 | 연산 시간 + `판정: B` |

### `choice2()` — 모드 2: data.json 분석

1. `load_data()`로 파일을 읽고, **dict이고 `patterns`가 dict인지 검사**합니다. 아니면 안내 후 종료합니다.
2. `names = sorted(data0["patterns"], key=natural_key)`로 패턴 이름을 자연 정렬합니다.
3. 각 이름마다 `analyze_case()`를 호출하고 `print_case()`로 출력하며 결과를 `results`에 모읍니다.
4. `print_performance(results)`, `print_summary(results)`를 호출합니다.

### `print_case(r)`

`analyze_case()`의 결과 하나를 출력합니다.

```
---size_5_1---
Cross 점수: 9
  X   점수: 1
판정: cross | expected: cross | PASS
```

- 통과: `PASS`
- 실패: `FAIL [분류 이름]`. 판정 라벨은 계산 전에 실패했으면 `N/A (계산 전 실패)`, 동점이면 `UNDECIDED`로 표시합니다.

### `print_performance(results)`

크기(N)별 평균 연산 시간을 표로 출력합니다.

```
크기 | 평균시간(ms) | 연산 횟수(곱셈)
5x5 | 0.0xxx | 50
```

- 시간이 기록된 케이스만 모아 크기별로 평균을 냅니다 (스키마 실패 케이스는 제외).
- 패턴 1개 = Cross, X 두 번의 MAC이므로 곱셈 횟수는 `2 × N²`입니다.
- `* 1000`으로 초를 ms로 환산합니다.

### `print_summary(results)`

통과·실패 개수와 **분류별 실패 보고서**를 출력합니다.

```
총 테스트: 8개
통과: 5개
실패: 3개

실패 케이스:
 [데이터/스키마 문제] 1건
   - size_7_1: 키 없음: filters/size_7
 [로직 문제] 1건
   - ...
```

실패가 없으면 `없음`을 출력합니다. 분류는 `SCHEMA` → `LOGIC` → `NUMERIC` 순서로 보여 줍니다.

### `main()`

메뉴를 보여 주고 `input("선택:")`으로 입력받아 `"1"`이면 `choice1()`, `"2"`이면 `choice2()`를 실행합니다. 파일을 직접 실행할 때만 호출되도록 `if __name__ == "__main__":`로 감싸져 있습니다.

---

## 8. 참고: 코드 속 알아둘 점

동작에는 문제가 없지만, 코드를 읽거나 이어서 수정할 때 알아두면 좋은 부분입니다.

| 위치 | 내용 |
|------|------|
| 삼중따옴표로 감싼 `mac` / `input_matrix` | 예전 버전을 주석처럼 남긴 문자열입니다. 실행되지 않습니다. |
| `choice2()`의 `b`, `calculating_time` | 이제 사용되지 않는 변수입니다. |
| `choice2()`의 `a` | "필터 로드 완료" 메시지에서 `size_5/13/25`를 **고정으로** 출력하며, 실제 검증 결과와는 무관합니다. |
| `choice1()` 동점 판정 | `abs(A - B) < EPSILON`(절대 오차만)을 쓰고, `analyze_case()`는 `is_tie()`(절대+상대)를 씁니다. 판정 기준이 서로 다릅니다. |
| `print_performance()` | "20회 반복 평균" 문구가 고정 문자열입니다. `measure()`의 `repeat` 값을 바꾸면 함께 고쳐야 합니다. |
| `load_data()` | 실패 시 `[]`를 반환하므로, 호출하는 곳에서 반환값 검사가 필요합니다 (`choice2`에 이미 있음). |
| `analyze_case()`의 시간 측정 | 스키마 검증을 통과한 뒤 NaN/inf 검사 **이전**에 이루어집니다. |
