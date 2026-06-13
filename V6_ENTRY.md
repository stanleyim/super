# V6 ENTRY — SUPER repo

기준 : v5 FROZEN (HEAD 5770438 + 338c71e, tag v5.0)
참조 : HANDOFF_v5.md (repo root, 565 lines)
작성 : 2026-06-13

---

## 1. 새 세션 첫 액션 (순서대로)

### [1.1] HANDOFF_v5.md 정독
우선 정독 section : §2.2 (RETAINED release), §13 (STEP 9 manifold), §16.3 (in-context fact), §18 (risk)

### [1.2] setup cell (clone)

```python
import os, sys, subprocess
if "GH_TOKEN" not in os.environ:
    from google.colab import userdata
    os.environ["GH_TOKEN"] = userdata.get("GH_TOKEN")
token = os.environ["GH_TOKEN"]
if not os.path.isdir("/content/super"):
    subprocess.run(["git","clone",
        f"https://x-access-token:{token}@github.com/stanleyim/super.git",
        "/content/super"], check=True)
os.chdir("/content/super")
print("HEAD:", subprocess.run(["git","rev-parse","HEAD"],
    capture_output=True, text=True).stdout.strip())
print("TAG :", subprocess.run(["git","describe","--tags"],
    capture_output=True, text=True).stdout.strip())
```

기대 출력 :
- HEAD = 338c71e (또는 후속 commit)
- TAG = v5.0 또는 v5.0-<n>-g<hash>

---

## 2. v6 SPEC LOCK (본 세션 사용자 결정)

```
A = 1 + 2       (STEP 10 + §2.1 unlock 결합)
B = a           (current Colab runtime)

세부 lock :
  1a  σ_i / T_THRESHOLD       DROP
  2c  T_star (manifold class) = CLASS III = {0, 1, 3, 4, 5}
  3a  cross-sectional allocation = equal weight
  4a  holding horizon H = 20
  5a  backtest = scripts/backtest_nonoverlap.py 재사용 시도
  6a  state source = data/processed/regime/regime.parquet  (Z_t per asset)
```

---

## 3. v6 phase 진행 계획

### Phase 1 — 기존 backtest 구조 분석
- read : scripts/backtest_nonoverlap.py
- read : scripts/generate_signal.py
- 확인 사항 :
  - signal interface (input cols : date, code, position?)
  - cost / horizon 처리 방식
  - output schema (trades.parquet / daily_portfolio.parquet)
- 판정 : 재사용 가능 / 부분 수정 / 신규 작성

### Phase 2 — v6 signal generator 작성
- 신규 파일 : `scripts/policy/build_signal_v6.py`
- input :
  - data/processed/regime/regime.parquet  (date, code, Z_t)
  - data/processed/edge/E_state.npy
- output :
  - data/processed/policy/signal_v6.parquet
  - cols : date, code, position (float, 0 또는 1/K)
- logic :

```
T_star = {0, 1, 3, 4, 5}
for each date t:
    candidates = {code i : Z_{i,t} ∈ T_star, Z_{i,t} != -1}
    K = |candidates|
    position[i,t] = 1.0/K if i ∈ candidates else 0.0
```

### Phase 3 — backtest 실행
- input : signal_v6.parquet + panel.parquet (close price)
- cost : 0.003 / 20 = 0.00015 per day (amortized)
  - 또는 turnover 비례 (사용자 결정)
- output :
  - data/processed/backtest_v6/daily_portfolio.parquet
  - data/processed/backtest_v6/trades.parquet
  - data/processed/backtest_v6/summary.json
- metric : Sharpe, Calmar, MDD, hit rate

### Phase 4 — v3/v4 baseline 비교
- baseline : NEXT_SESSION.md §1.4
  - Sharpe 1.806 / Calmar 2.473 / MDD -22.96% (단일 split)
  - walk-forward 3/6 pass, CV=1.21
- v6 vs baseline : 차이 + 원인 분석

### Phase 5 — COMMIT + FREEZE v6
- bucket A : scripts/policy/build_signal_v6.py
- bucket B : data/processed/policy/signal_v6.parquet
- bucket C : data/processed/backtest_v6/*
- bucket D : HANDOFF_v6.md (이 파일 구조 참고하여 작성)
- tag v6.0

---

## 4. 참조 번호 (다음 세션 즉시 참조용)

### 4.1 핵심 산출값 (v5 §16.3 발췌)

**[REF-A] E_state (8-vec, forward log return)**

```
i   N         E_state         bps/day
0   122,957   +0.000526       +5.26
1   51,054    +0.001064       +10.64
2   47,987    -0.001393       -13.93
3   7,525     +0.001054       +10.54
4   8,638     +0.008801       +88.01
5   173,024   +0.001230       +12.30
6   50,576    -0.000415       -4.15
7   50,315    -0.000187       -1.87
```

**[REF-B] T_star = CLASS III**

```
T_star = {0, 1, 3, 4, 5}
N(T_star) = 363,198 / 512,336 (70.89%)
```

**[REF-C] regime label_map (v5 §6, STEP 2 산출)**

```
{0:T, 1:T, 2:T, 3:Tr, 4:T, 5:S, 6:Tr, 7:Tr}
  T  = TRANSITION,  Tr = TREND,  S = SHOCK
```

**[REF-D] Stability S(i) (v5 §10)**

```
i=0: 0.9841   i=1: 0.0644   i=3: 0.4232   i=4: 0.9628   i=5: 0.9938
```

**[REF-E] Basin (v5 §11)**

```
core   = {5}     stable = {0, 4}
bridge = {3}     escape = {1}
```

**[REF-F] §2.1 RETAINED constants (release status)**

```
cost_rt        = 0.003       (v6 H amortized 적용 : 0.00015/day)
T_THRESHOLD    = 2.0         (v6 DROP)
MIN_VISITS     = 100         (v6 state-level 미적용, 8/8 통과)
TRADEABLE_REG  = {TREND,RANGE} (v6 DROP — CLASS III 적용)
H              = 20          (v6 적용 — holding horizon)
```

### 4.2 핵심 파일 경로 (v5 commit)

```
[FILE-1]  data/processed/regime/regime.parquet
          cols: date, code, state_id, Z_t, R_t
          rows: 577,311 / codes: 261 / dates: 2,729

[FILE-2]  data/processed/transition/T.npy        (8,8) float64
[FILE-3]  data/processed/transition/C.npy        (8,8) int64
[FILE-4]  data/processed/edge/E_state.npy        (8,) float64
[FILE-5]  data/processed/edge/E_transition.npy   (8,8) float64
[FILE-6]  data/processed/edge/N_state.npy        (8,) int64
[FILE-7]  data/processed/edge/N_transition.npy   (8,8) int64
[FILE-8]  data/processed/state_vector/panel.parquet
[FILE-9]  scripts/backtest_nonoverlap.py         ← v3/v4 baseline
[FILE-10] scripts/regime/build_regime.py         ← BUG-1 fix 적용
```

### 4.3 미해결 항목 (v5 §15)

```
[PEND-1] STEP 8 FULL PRECISION (Colab eig(T.npy) full float64)
         → 정성 영향 무 추정, 보류 가능
[PEND-2] §2.1 RELEASE 정식 §14 unlock block 작성
         → v6 HANDOFF 에 포함 권장
[PEND-3] STEP 5~9 file persistence (build_omega.py 등)
         → v5 §16.3 receipts 보존되므로 보류 가능
[PEND-4] S3-B/C/D unlock
         → 별도 영역, v6 범위 외
```

---

## 5. v6 작업 규칙

### 5.1 응답 효율
- 응답 1건 = 코드 1개 paste OR stdout 분석 1개
- 옵션 enumeration 최소화 (default 권장 시 즉시 진행)
- L1 적용 = 추측 위험 있을 때만, default 권장 가능 시 명시 후 진행

### 5.2 spec lock 형식
- §11.3 form 권장 (id="..." 태그)
- 산술 결과는 Claude bash_tool 직접 실행
- 추정 표현 금지 ("approximate", "likely" 등)

### 5.3 commit 규칙
- bucket 단위 commit (atomic)
- HANDOFF_v6.md 별도 commit
- tag v6.0 push 시 deployment lock

---

## 6. v6 진입 신호

새 세션에서 다음 한 줄로 시작 :

```
V6 START. spec lock 적용 (V6_ENTRY.md §2). Phase 1 진행.
```

또는 spec 변경 시 :

```
V6 START. spec 변경: 2c → 2b (CLASS II). 기타 V6_ENTRY.md §2 그대로.
```

---

## 7. END

v6 완료 시 HANDOFF_v6.md 작성 + tag v6.0 push.
이후 v7 진입은 V7_ENTRY.md 작성.
