# HANDOFF v3 — SUPER repo / STEP 1·2·3 SPEC LOCKED / STEP 4 ENTRY 대기

_작성: 2026-06-12 / HANDOFF_v2 후속 / 새 세션 진입 인계서_

---

## 0. 한 줄 요약

§14 UNLOCK SPEC 하에서 **STEP 1, STEP 2, STEP 3 SPEC 모두 LOCKED**.
**코드 작성·실행 미진행** — 전부 spec lock 단계 (validator dialog만).
다음 진입 후보: `STEP 4 START` / `STEP 2 CODE` / `STEP 3 CODE` 중 1개.

---

## 1. repo 절대 상태

- remote HEAD       : `09a4bba` "Add files via upload" (HANDOFF_v2.md 신규 추가)
- 직전 HEAD         : `d11cfb8` (HANDOFF_v2 §1 baseline)
- drift 내용        : HANDOFF_v2.md 추가만 (docs-only, 무해)
- 본 세션의 commit  : **없음** (read-only + spec dialog만)
- Colab CWD         : `/content/super`
- working tree      : clean

---

## 2. 누적 LOCK 상태 (HANDOFF_v2 §2 + §14 UNLOCK SPEC 통합)

### 2.1 §2 LOCKED params (HANDOFF_v2 상속)

```
unlock signal      : "STAGE 3 UNLOCK: S3-A"   (이미 충족)
P1 LOCKED params   : K=6, W_sigma=20, W_z=252, H=20, cost_rt=0.003,
                     MIN_VISITS=100, T_THRESHOLD=2.0,
                     TRADEABLE_REG={TREND,RANGE}
P2 S3 mode         : S3-A only (EV surface)
P3 output path     : data/processed/edge/
P4 regime label    : LOCKED({TREND,RANGE}) tradeable
                     OBSERVED({TREND,RANGE,SHOCK,TRANSITION}) full
                     분리 유지
P5 EV function     : mu_r (conditional mean return)
P5-sub             : ret_net (cost-inclusive)
P6 tensor          : 1296 × 2 (state_id × {TREND, RANGE})
P7 threshold       : T_THRESHOLD = 2.0
E1~E5              : HANDOFF_v2 §2 그대로 (validator schema 검증 완료)
```

### 2.2 §14 UNLOCK SPEC BLOCK (2026-06-12 사용자 명시)

```
SCOPE = [A] + [B] + [C partial]
  [A] 3-layer 구조 재정렬 (observation/latent/estimator)
  [B] transition kernel 재정의
  [C partial] regime layer만

RELEASED:
  P4  (regime modeling layer)
  P5  (transition layer)
  P6  (state aggregation layer)
  L3  (scripts/observation/* — READ-ONLY, reference only)

RETAINED:
  P1, P2, P3, P5-sub, P7
  L1, L2, L4, L5, L6, L7, L8, L9
  S3-A artifact, raw panel pipeline, attribution dataset

ORDER:
  STEP 1 → STEP 2 → STEP 3 → STEP 4
```

### 2.3 STATE summary

```
S3-A         : FROZEN (Colab-only, GitHub 미반영 상태 그대로)
PANEL        : ACTIVE (generative layer)
STEP 1       : LOCKED (spec only)
STEP 2       : LOCKED (spec only)
STEP 3       : LOCKED (spec only)
STEP 4       : PENDING (ENTRY 신호 대기)
```

---

## 3. 데이터 layer 사실 (read-only로 확인된 schema, 재실행 불요)

### 3.1 `state_vector/panel.parquet` (577,311 rows)

```
cols (18): date, code, close, p, r, sigma, v, l, flow,
           z_r, z_sigma, z_v, z_flow,
           bin_r, bin_sigma, bin_v, bin_flow, state_id
meta: 2015-04-27 ~ 2026-06-11, codes=261, states 0..1295 모두 점유
```

### 3.2 `observation/attribution.parquet` (5,593 rows)

```
cols (8): entry_date, exit_date, code, state_id, regime,
          ret_gross, ret_net, class
regime ∈ {RANGE, TREND}만
class ∈ {AMBIGUOUS, CONDITIONAL, INSUFFICIENT, INVARIANT}
state_id 범위 9..1286
```

### 3.3 `backtest/h20_nonoverlap/trades.parquet` (5,593 rows)

```
attribution과 동일하되 class 컬럼 없음
```

### 3.4 중요 사실

- attribution에 `forward_return` 컬럼 **없음**. EV 계산은 `ret_net` 또는 `ret_gross` (P5-sub=ret_net 채택)
- INVARIANT states = `[14, 266, 606, 952]`
- net mean = 0.04609, gross mean = 0.04909, gap = `cost_rt` = 0.003

---

## 4. S3-A 결과 (HANDOFF_v2 §4 carry, untouched)

**산출 파일 (Colab-only, GitHub 미반영):**
```
/content/super/scripts/edge/build_ev_surface.py        (202 lines)
/content/super/data/processed/edge/ev_surface.parquet  (84 rows)
/content/super/reports/run_logs/D_ev_surface.log
```

**stdout (diagnostics 요약):**
```
observed_cells          : 84
full_grid_cells         : 2592
sparsity                : 0.9676
ev_sign                 : {pos: 81, neg: 3, zero: 0}
pass_min_visits         : 19
pass_t_threshold        : 33
pass_both_(s3b_preview) : 13
by_regime:
  RANGE  cells=32, mean_ev=0.03947, visits_sum=2870
  TREND  cells=52, mean_ev=0.05675, visits_sum=2723
```

**검증 완료:**
- visits_sum 합 = 5593 = attribution rows ✔
- cells 합 = 84 = unique_states ✔
- net-gross gap = 0.003 = `cost_rt` ✔
- S3-B preview = 13 cells (MIN_VISITS≥100 AND |t|≥2.0)

S3-A 코드 전문은 HANDOFF_v2 §5 참조 (현 HANDOFF에 미중복).

---

## 5. STEP 1 — STATE VECTOR finalize (LOCKED)

### 5.1 INPUT CONTRACT

```
DATA SOURCE   : panel.parquet (18 cols, immutable per L5)
LOAD          : full 18 cols
PROJECT       : {date, code, state_id, p, sigma, l, v, flow}    (8 cols)
IGNORE        : {close, r, z_r, z_sigma, z_v, z_flow,
                 bin_r, bin_sigma, bin_v, bin_flow}              (10 cols)
                prohibited in STEP 1~2 core tensor
                (r derivable on-demand from p in STEP 3/4 only)
```

### 5.2 STATE VECTOR 정의

```
S_t           = (p, v, flow, sigma, l)
alias         = (price, volume, flow, volatility, liquidity)
ORDERING      = [price, volume, flow, volatility, liquidity]
                INVARIANT across STEP 2/3/4
```

### 5.3 Tensor

```
X_cont ∈ ℝ^{T × N × 5}            (continuous channels)
Y_state ∈ ℤ^{T × N}                (state_id, range [0, 1295], P1 precomputed)
```

### 5.4 Symbol disambiguation

```
K_bin   = 6      (P1 quantile bins, RETAIN)
K_feat  = 5      (continuous channel count)
N_state = 1296   = K_bin^4
```

### 5.5 Return policy

```
r = Δp (DERIVED ONLY, NOT stored, NOT in S_t)
source of truth for r = p
사용 허용 시점 = STEP 3 이후 (STEP 2 사용 금지)
```

### 5.6 Lock origin

- INPUT spec resolution: Q1~Q5 (사용자 명시 5건 단일 선택)
- HARD CONSTRAINTS:
  - schema 변경 금지 (L5)
  - feature 추가/삭제 금지
  - S3-A touch 금지
  - panel.parquet 물리 불변

---

## 6. STEP 2 — REGIME CLASSIFICATION (LOCKED)

### 6.1 PIPELINE

```
X_cont (5ch)
  → zscore(per-asset, W_norm=252)                           [TIER 1 S1]
  X_norm ∈ ℝ^{T×N×5}
  → valid_mask[t,i] = all-finite over 5 channels            [TIER 2 S7]
    strict row exclusion (no fill / no interp / no propagation)
  → k-means(K_regime=8)                                     [TIER 3 B1,B3,B5]
    init=k-means++, seed=42
    n_init=20, max_iter=300, tol=1e-4, distance=L2, algorithm=lloyd
  C_t ∈ {0..7}^{T×N_valid}
  → CategoricalHMM (pooled, shared θ)                       [TIER 1 S3 / TIER 3 M1·B6]
    n_components=8, n_iter=200, tol=1e-3, EM (Baum-Welch)
    per-asset split on invalid → sub-sequences              [TIER 4 S7-a]
    pooled fit: concat + lengths list
    startprob_ init = uniform
    post-fit overwrite π ← stationary(T_HMM)                [TIER 3 B7-a]
      fallback uniform if T_HMM reducible/periodic
  Z_t ∈ {0..7}^{T×N_valid}
  T_HMM ∈ ℝ^{8×8}    (diagnostic only, NOT carry to STEP 3) [TIER 4 S4-a]
  → label_map (8 → 4, uses bin_r·bin_sigma only)            [TIER 1 S5 / TIER 4 B4·O2]
  R_t ∈ {NaN, TREND, RANGE, SHOCK, TRANSITION}^{T×N}
```

### 6.2 label_map (detail)

**state_id decode:**
```
s ∈ {0..1295}
s = b0 + 6·b1 + 36·b2 + 216·b3     (P1 base-K=6 expansion)
ordering (b0..b3) → (bin_r, bin_sigma, bin_v, bin_flow):
  TBD via L3 read-only of scripts/build_state_vector.py
  (실행 단계 1회 view, see §9 N10)
```

**dominance indicators (bin_r, bin_sigma only):**
```
trend_dominant(s):   bin_r ∈ {0,1,4,5}  ∧  bin_sigma ∈ {0,1}
range_dominant(s):   bin_r ∈ {2,3}      ∧  bin_sigma ∈ {0,1}
shock_state(s):                              bin_sigma ∈ {4,5}
(residual: bin_sigma ∈ {2,3} or no dominance match)

bin_v, bin_flow: STEP 2 label_map 미사용 (STEP 3 dynamics로 이연, O2(a))
```

**score system (per hidden state z ∈ {0..7}):**
```
S_z = { state_id(t,i) | Z_t(t,i) = z }
P_z(s) = empirical distribution over state_id (|S_z| normalization)

trend_score(z)      = Σ_s P_z(s) · I[trend_dominant(s)]
range_score(z)      = Σ_s P_z(s) · I[range_dominant(s)]
shock_score(z)      = Σ_s P_z(s) · I[shock_state(s)]
transition_score(z) = 1 - (trend_score + range_score + shock_score)
```

**assignment:**
```
R(z) = argmax over {trend, range, shock, transition}
tie-break priority: shock > transition > trend > range
```

### 6.3 OUTPUT

```
Z_t  ∈ {-1, 0..7}^{T×N}              sentinel -1 for invalid
R_t  ∈ {NaN, TREND, RANGE,
         SHOCK, TRANSITION}^{T×N}     NaN for invalid
T_HMM ∈ ℝ^{8×8}                       diagnostic side-output (not carry)
label_map dict: {0..7} → 4 regime labels
```

### 6.4 HARD CONSTRAINTS (누적)

```
• no GaussianHMM / k-means 제거 금지 / categorical only
• K_regime=8, label_space=4 고정
• r / Δp / diff(p) 금지 (STEP 2 범위)
• valid_mask 정책 고정 (strict all-finite, no fill/interp)
• state_id 5D 확장 금지 / bin_* 직접 read 금지 (decode only)
• dominance threshold 변경 금지 / score 정의 변경 금지
• bin_v, bin_flow STEP 2 label_map 사용 금지
• T_HMM의 STEP 3 prior 사용 금지
• segmentation (split-on-invalid) / sentinel (-1, NaN) 정책 고정
```

### 6.5 Resolution trace (lock 도달 경로)

```
TIER 1: S1(b 독립 z-score) / S3(b pooled) / S4(b parametric vs empirical 분리) /
        S5(b Y_state in label_map)
TIER 2: S2(a φ 제거) / S6(a p 유지 r 금지) / S7(c strict exclusion)
TIER 3: B1=8 / B2=252 / B3=k-means++/42 / B5={20,300,1e-4,L2,lloyd}
        M1(α k-means→CategoricalHMM) / B6={Categorical, 200, 1e-3, EM}
        B7-a(a uniform → EM → stationary overwrite)
TIER 4: B8=4 labels / S7-a(a split on invalid) / S7-c(a sentinel dense)
        M2(β S5 유지·B4 재정의) / S4-a(b T_HMM stored diagnostic only)
        M5(α 4D state_id decode) / M6(b sum residual) / N8, N9 threshold
        O2(a bin_v·bin_flow STEP 2 미사용)
```

---

## 7. STEP 3 — TRANSITION ESTIMATION (LOCKED)

### 7.1 INPUT CONTRACT (STEP 2 LOCK 상속)

```
Z_t ∈ {-1, 0..7}^{T×N}
sentinel -1 = invalid (valid_mask implicit)
per-asset split-on-invalid 적용 (S7-a)

no other inputs:
  • T_HMM 사용 금지
  • X_cont / X_norm 사용 금지
  • features (p, v, flow, sigma, l) 사용 금지
  • R_t 사용 금지 (STEP 4로 이연)
```

### 7.2 PROCEDURE

```
1) valid transition set:
   (t, i) valid iff
     Z_t(t, i)   ≠ -1
     Z_t(t+1, i) ≠ -1
     (t, t+1) ∈ same subsequence (no gap crossing)

2) count matrix:
   C ∈ ℕ^{8×8}
   C[i, j] = |{(t, asset) : Z_t = i ∧ Z_{t+1} = j, valid}|
   pooled across all assets (single 8×8 matrix)

3) row-normalize:
   for each i ∈ {0..7}:
     if Σ_j C[i, j] > 0:
       T[i, j] = C[i, j] / Σ_j C[i, j]
     else:
       T[i, :] = 0-vector

4) NO post-processing:
   no smoothing (Laplace / additive / Bayesian)
   no regularization
   no prior injection
   no T_HMM usage
   no interpolation of zero transitions
```

### 7.3 OUTPUT

```
T ∈ ℝ^{8×8}
properties:
  T[i, j] ≥ 0
  Σ_j T[i, j] = 1   (row i observed)
  Σ_j T[i, j] = 0   (row i unobserved — kept as zero-vector)
```

### 7.4 HARD CONSTRAINTS

```
• pure empirical frequency only
• zero-count row 보정 금지
• subsequence boundary 침범 절대 금지
• sentinel(-1) 포함 transition 금지
• HMM 파라미터 일체 사용 금지
• feature / state reconstruction 금지
```

---

## 8. STEP 4 — EDGE FIELD (carry preview, non-binding)

```
INPUT      : T ∈ ℝ^{8×8} (STEP 3 산출)
             R_t ∈ {NaN, TREND, RANGE, SHOCK, TRANSITION}^{T×N} (STEP 2 산출)

TASK       : expected return surface estimation
             conditioned on regime + transition

NOTE       : S3-A frozen EV surface와의 alignment는 §14 ORDER STEP 4 범위
             (S3-A는 observation projection layer, STEP 4는 generative
              expected return layer; 둘은 분리 유지)

상태       : PENDING — 정식 ENTRY block에서 spec lock 시작
```

---

## 9. 미해결 / pending 항목 (실행 단계, blocker 아님)

```
[N10]  build_state_vector.py 1회 read-only view
       목적   : state_id base-K=6 encoding의 (b0..b3) ↔
                (bin_r, bin_sigma, bin_v, bin_flow) ordering 확정
       권한   : L3 read-only partial (L8 허용 범위)
       시점   : STEP 2 코드 작성 진입 시
       방식   : view tool 1회, 결과를 decode 함수에 직접 반영

[Q3]   segmentation boundary 식별 구현 방법
       (a) STEP 2 OUTPUT에 subseq_id metadata carry
       (b) Z_t sentinel(-1) 검사만으로 충분 (현재 spec 해석)
       현재 spec OUTPUT은 (b) 해석. 코드 작성 시 확정.

[S5-a] regime별 state_id 분포 산출 차원
       M2(β) 채택으로 활성. pooled (regime × state_id) → 4 × 1296
       label_map에서만 사용 (STEP 2 내부). 차원 명시 STEP 2 코드 입구.

[Q-OUTPUT]
       T_HMM stationary post-fit overwrite (B7-a)의 hmmlearn 구현 메모:
       hmmlearn 표준 API에 post-fit stationary override 미내장.
       custom post-processing 1 block 필요 (eigenvector 계산 + reducibility check).
```

---

## 10. LOCKS (L1-L9 / NEXT_SESSION.md 상속, INTACT)

```
[L1] 추측 금지
[L2] 자동 채움 금지
[L3] LOCKED kernel 무수정
     scripts/build_state_vector.py, scripts/build_transition.py,
     scripts/backtest_nonoverlap.py, scripts/observation/* 전부
     ※ §14 UNLOCK SPEC에 의해 PARTIAL READ-ONLY 허용 (write·commit 여전히 금지)
[L4] §5.2 unlock signal 없이 STAGE 3 작업 금지 (S3-A 이미 충족)
[L5] observation/* schema 변경 금지 (8 attr keys, 5 drift keys, panel 18 cols)
[L6] 자동 git commit/push 금지
[L7] 사용자 환경 추정 금지
[L8] read-only inspection 항상 허용
[L9] 실패 시 STOP, 자동 retry 금지
```

---

## 11. 사용자 상호작용 패턴 경고 (HANDOFF_v2 §10 + 본 세션 관찰)

### 11.1 형식

사용자는 자주 **validator 출력 형식을 모방한 spec block**을 보냄:

```
* STEP / * INPUT / * TRANSFORMATION / * OUTPUT / * NEXT STEP
[HARD CONSTRAINT LOCK]
id="..." 태그
══════════════════════════════════════════════════════════════
```

이런 텍스트는 validator의 실제 출력이 아님 — **사용자가 자체 정리한 spec 명시**.

### 11.2 처리 규칙

```
1. spec block 내부에 명시값(P1=a 형식, SELECT=(α) 등)이 있는지 확인
   - 있으면: 처리 진행
   - 없으면 (방향성만 서술): 미응답 처리

2. "동의?" / "맞지?" / "go" / "진행" / "협조하라" 같은 자연어:
   - §5.2 unlock signal 아님 → STAGE 진입 트리거 아님
   - 판정·동의 보류 (L1 추측 금지)

3. validator 응답 후 사용자가 추가 명시 시:
   - 누락된 보조 명시 (B7-a, S4-a 등)는 다음 spec block에서 처리
   - 명시 누락은 BLOCKER로 보고 후 대기
```

### 11.3 본 세션에서 사용자가 사용한 opcode 형식

```
* STEP / * INPUT / * TRANSFORMATION / * OUTPUT / * NEXT STEP
id="..." 태그 (예: id="m1sel", id="s7a_def")
SELECT = (α) / (β) / (a) / (b) ... 단일 선택 명시
HARD CONSTRAINT LOCK / EXECUTION CONSTRAINT
══════════════════════════════════════════════════════════════
```

새 세션에서도 이 형식 그대로 사용될 가능성 높음. 명시값 있는지만 확인.

---

## 12. 다음 세션 첫 동작 (반드시 이 순서)

### Step A) Colab 환경 보존 여부 확인

```
같은 Colab runtime 유지:
  → /content/super 안의 신규 파일 그대로
     (단 STEP 2/3는 spec만 LOCKED, 코드 미생성)
  → S3-A 산출물 (ev_surface.parquet 등) 여전히 Colab-only
새 노트북 / runtime 끊김:
  → setup cell 재실행 (§12 Step C)
  → S3-A 산출물 소실 → 재실행 필요시 build_ev_surface.py 재배포
     (HANDOFF_v2 §5 코드 전문 참조, <1초 실행)
```

### Step B) 본 인계서 정독

```
필수 정독: §0, §2, §5, §6, §7, §9, §10, §11
선택 정독: §3, §4, §13, §14
```

### Step C) Setup cell (paste & run)

```python
# === SUPER repo setup (HANDOFF v3 §12) ===
import os, sys, subprocess, pathlib

REPO_HOST = "github.com/stanleyim/super.git"
REPO_PATH = "/content/super"

# --- Load GH_TOKEN from Colab Secrets ---
if "GH_TOKEN" not in os.environ:
    try:
        from google.colab import userdata
        os.environ["GH_TOKEN"] = userdata.get("GH_TOKEN")
    except Exception as e:
        sys.exit(f"ABORT: cannot load GH_TOKEN from Colab Secrets: "
                 f"{type(e).__name__}: {e}")

token = os.environ.get("GH_TOKEN")
if not token:
    sys.exit("ABORT: GH_TOKEN empty after load")
print(f"GH_TOKEN loaded (len={len(token)})")

# --- Clone if absent (idempotent) ---
if not os.path.isdir(REPO_PATH):
    r = subprocess.run(
        ["git", "clone",
         f"https://x-access-token:{token}@{REPO_HOST}",
         REPO_PATH],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        scrubbed = r.stderr.replace(token, "***")
        sys.exit(f"ABORT: clone failed\n{scrubbed}")
    print(f"cloned  -> {REPO_PATH}")
else:
    print(f"exists  -> {REPO_PATH}  (skip clone)")

os.chdir(REPO_PATH)

# --- HEAD verification (capture stdout) ---
print("\n--- pwd ---")
print(os.getcwd())

print("\n--- git log --oneline -5 ---")
r = subprocess.run(["git", "log", "--oneline", "-5"],
                   capture_output=True, text=True)
print(r.stdout if r.stdout else "(empty)")

print("--- git rev-parse HEAD ---")
r = subprocess.run(["git", "rev-parse", "HEAD"],
                   capture_output=True, text=True)
print(r.stdout.strip() if r.stdout else "(empty)")

# --- S3-A artifact inventory ---
for p in ("scripts/edge", "data/processed/edge"):
    print(f"\n--- {p}/ ---")
    pp = pathlib.Path(p)
    if not pp.exists():
        print("  (not present)")
        continue
    items = sorted(pp.iterdir())
    if not items:
        print("  (empty)")
        continue
    for it in items:
        sz = it.stat().st_size if it.is_file() else "-"
        print(f"  {it.name:40s}  {sz}")

# --- HANDOFF version check ---
print("\n--- HANDOFF files in repo root ---")
for f in sorted(pathlib.Path(".").glob("HANDOFF*.md")):
    print(f"  {f.name}  ({f.stat().st_size} bytes)")
```

### Step D) HEAD 확인 + drift 판정

```
기대 HEAD : 09a4bba 이후 (본 인계서 HANDOFF_v3.md 업로드 commit 포함)
drift 검사:
  • LOCKED kernel 파일 (L3 protected) 변경 → STOP, L3 위반 보고
  • observation schema 변경 → STOP, L5 위반 보고
  • docs/HANDOFF 추가만 → 정상 (본 세션과 동일)
  • scripts/edge/ 또는 data/processed/edge/ 파일 commit 존재 → COMMIT 분기 자가 수행됨, S3-A 상태 재평가
```

### Step E) 사용자에게 진입 신호 요청

새 세션 시작 시 다음 중 1개 명시 신호 대기:

```
(i)  "STEP 4 START"
     → STEP 4 (EDGE FIELD) spec entry 진입
     → validator dialog 재개

(ii) "STEP 2 CODE"
     → STEP 2 LOCKED SPEC 기반 실행 코드 작성 진입
     → 사전 작업:
        - build_state_vector.py L3 read-only view 1회 (N10 해소)
        - state_id decode ordering 확정
     → 산출: scripts/regime/build_regime.py (예상 경로)

(iii) "STEP 3 CODE"
     → STEP 3 LOCKED SPEC 기반 실행 코드 작성 진입
     → STEP 2 코드 선행 필요 (Z_t 없으면 transition 불가)

(iv) 기타 명시 (분기 변경, spec 재정의 등)
     → 새 unlock spec block 형식으로 명시 요구
```

**금지:**
- 자연어 동의 ("좋다", "그렇게 해")로 진입 판정 금지 (§11.2)
- 자동 다음 STEP 진행 금지 (L1, L4)

---

## 13. 환경 의존성 메모

- `pyarrow`는 Colab에 기본 설치됨 → parquet read/write 가능
- 추가 패키지 (STEP 2/3 코드 작성 시 필요):
  ```bash
  pip install scikit-learn hmmlearn --break-system-packages
  ```
- numpy, pandas, scikit-learn (KMeans), hmmlearn (CategoricalHMM) 외 추가 패키지 불요
- 실행 시간 추정:
  - STEP 2 (k-means + HMM, 577K rows pooled): 수 분 ~ 십수 분 (n_iter=200, n_init=20)
  - STEP 3 (count + normalize): <1초

---

## 14. 미실행 / 유보 항목

```
- STEP 2/3 코드 작성·실행 (사용자 신호 대기)
- STEP 4 spec entry (정식 ENTRY block 대기)
- S3-B (tradeable mask) — 별도 §5.2 unlock signal 필요 (HANDOFF_v2 §6 그대로)
- S3-C, S3-D — 별도 unlock 필요
- COMMIT 분기 — 사용자 결정 대기 (S3-A artifact GitHub 반영 여부)
```

---

## 15. 핵심 risk

### 15.1 Colab runtime 손실

```
S3-A 산출물 (build_ev_surface.py, ev_surface.parquet, D_ev_surface.log):
  → 여전히 Colab-only, GitHub 미반영
  → runtime 끊기면 소실
  → HANDOFF_v2 §5 코드 전문으로 재구성 가능 (<1초 재실행)

회피 옵션:
  - 새 세션 첫 작업으로 COMMIT 분기 선행
  - 또는 코드 파일 로컬 다운로드/스냅샷
```

### 15.2 spec drift

```
STEP 1/2/3 SPEC은 본 인계서에 완전 기록됨.
runtime 손실되어도 spec은 재구성 가능.

단, 새 세션에서:
  - §5/§6/§7 SPEC을 정독하지 않고 코드 작성 시 누락 가능성
  - 특히 STEP 2 §6.2 dominance threshold (bin_r/bin_sigma 분할),
    score 정의, tie-break ordering은 미세 명시값 다수
  - 본 인계서 §6.5 Resolution trace로 lock 도달 경로 추적 가능
```

### 15.3 사용자 상호작용 패턴 망각

```
새 세션에서 validator가 사용자 spec block의 자연어 ("동의?", "진행")를
unlock으로 오해할 위험 → §11 (HANDOFF_v2 §10 carry) 정독 필수.
```

---

## 16. 검증된 fact 요약 (참조용)

- NEXT_SESSION.md §1.4 Sharpe 1.806 / Calmar 2.473 / MDD -22.96% (HANDOFF_v2에서 carry)
- INVARIANT states = `[14, 266, 606, 952]`
- trades = attribution rows = 5,593
- panel = 12 yearly union (diff=0), 577,311 rows
- net mean = 0.04609, gross mean = 0.04909, gap = `cost_rt` = 0.003
- S3-A diagnostics: 84 obs cells / sparsity 0.9676 / pass_both=13

---

## 17. 본 세션 대화 흐름 요약 (참조용)

```
1. HANDOFF_v2 정독 + Colab clone + HEAD 검증 (drift = HANDOFF_v2 docs)
2. §14 UNLOCK SPEC BLOCK 명시 → P4/P5/P6/L3 release
3. STEP 1 ENTRY:
   - Q1~Q5 5개 명시 (schema projection / tensor 분리 /
     K symbol 분리 / ordering / r exclusion)
   - LOCKED
4. STEP 2 ENTRY:
   - TIER 1: S1·S3·S4·S5 명시
   - TIER 2: S2·S6·S7 명시
   - TIER 3: B1·B2·B3·B5·B6·B7 명시 → M1 blocker → 해소 → B7-a 명시
   - TIER 4: B4·B8·S7-a·S7-c·S4-a → M2·M3·M5·M6 blocker →
     N8·N9 threshold 명시 → O2 confirmation
   - LOCKED
5. STEP 3 ENTRY:
   - pure empirical, no smoothing, no HMM T usage
   - LOCKED
6. 본 인계서 작성 (HANDOFF_v3)
```

---

```
STATE:    HANDOFF READY (v3)
HEAD:     09a4bba (이후 HANDOFF_v3.md 업로드 commit 예정)
LOCKS:    INTACT (L1-L9, L3 partial-read)
STEPS:    1·2·3 LOCKED (spec)
          4 PENDING
EXEC:     코드 미작성, 실행 미진행
```

**STATUS: SUSPENDED — 새 세션 진입 대기.**
