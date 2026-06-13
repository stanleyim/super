# HANDOFF v4 — SUPER repo / STEP 1·2·3 EXECUTED + STEP 4 CODE UPLOADED / PENDING_EXEC

_작성: 2026-06-13 / HANDOFF_v3 후속 / STEP 4 dry-run 진입 직전 인계서_

---

## 0. 한 줄 요약

HANDOFF_v3 §0~§17 정독 후 본 세션에서:
- **STEP 2** SPEC carry → CODE 작성 → 실행 → 저장 완료
- **STEP 3** SPEC carry → CODE 작성 → 실행 → 저장 완료
- **STEP 4** SPEC LOCK (n7x4qp + n11 + N12·N13·N14) → CODE 작성 → GitHub 업로드 완료
- **STEP 4 dry-run 미실행** ← 다음 세션 첫 작업

산출:
- `data/processed/regime/`     ← Colab-only (commit 안 됨)
- `data/processed/transition/` ← Colab-only
- `data/processed/edge/`       ← 미생성 (STEP 4 실행 후 산출)

---

## 1. repo 절대 상태

```
remote HEAD : (build_edge.py upload commit, hash 미확인)
직전 HEAD   : 28cbb0c "Add files via upload"          (build_transition.py 추가)
이전        : c46f9b8 "Delete scripts/regime/build_reg.py"   ← HANDOFF_v3 §1 baseline
이전        : c9e3072 "Add files via upload"          (build_regime.py 추가)
이전        : 0264b92 "Create build_reg.py"           (오타 파일, c46f9b8에서 삭제됨)
이전        : 85d8859 "Add files via upload"          (HANDOFF_v3 업로드)
이전        : 09a4bba "Add files via upload"          (HANDOFF_v2 업로드, v3 §1 baseline)

Colab CWD   : /content/super
working tree: clean (Colab-only artifacts 별도)
본 세션 commit: 3건 + (build_edge.py 1건 — hash 미확인)
  • Create build_reg.py            (오타, 자가 삭제)
  • Add files via upload           (build_regime.py)
  • Delete build_reg.py
  • Add files via upload           (build_transition.py)
  • Add files via upload           (build_edge.py)     ← 마지막
```

---

## 2. 누적 LOCK 상태 (HANDOFF_v3 §2 + STEP 4 lock 추가)

### 2.1 v3 §2 그대로 (carry)

```
P1 LOCKED       : K=6, W_sigma=20, W_z=252, H=20, cost_rt=0.003,
                  MIN_VISITS=100, T_THRESHOLD=2.0,
                  TRADEABLE_REG={TREND,RANGE}
P2 S3 mode      : S3-A only (EV surface)
P3 output path  : data/processed/edge/
P4 regime label : LOCKED({TREND,RANGE}) tradeable
                  OBSERVED({TREND,RANGE,SHOCK,TRANSITION}) full
P5 EV function  : mu_r (conditional mean return)
P5-sub          : ret_net (cost-inclusive)
P6 tensor       : 1296 × 2 (state_id × {TREND, RANGE})
P7 threshold    : T_THRESHOLD = 2.0
E1~E5           : v2 §2 그대로

§14 UNLOCK SPEC (v3 carry):
  RELEASED : P4 / P5 / P6 / L3 (read-only partial)
  RETAINED : P1, P2, P3, P5-sub, P7, L1, L2, L4~L9
  ORDER    : STEP 1 → 2 → 3 → 4
```

### 2.2 STEP 1·2·3 SPEC LOCKED (v3 §5/§6/§7 그대로, 본 세션 변경 없음)

### 2.3 STEP 4 SPEC LOCK (본 세션 신규)

```
id="n7x4qp_r_convention" → SELECT = (B) FORWARD
id="n11_estate_inclusion" → N11 = (β) SYMMETRIC
                            N12 = panel merge 채택
                            N13 = log return 채택
                            N14 = NaN unobserved 채택

DEFINITIONS (LOCKED):
  r_t              := p_{t+1} - p_t       (p = log(close); Δp = log return)
  E_state[i]       := E[r_t | Z_t = i]                  (β SYMMETRIC)
  E_transition[i,j]:= E[r_t | Z_t = i, Z_{t+1} = j]

INCLUSION (β):
  Z_t ≠ -1  AND  Z_{t+1} ≠ -1  AND  r_t notna
  (STEP 3 valid 조건과 정확히 동일 → algebraic identity 성립)

MISSING CELL:
  N_{i,j} = 0  →  E_transition[i,j] = NaN  (no fill, no smoothing)
  N_i = 0      →  E_state[i] = NaN

INVARIANT:
  E_state[i] ≡ Σ_j T[i,j] · E_transition[i,j]    (verify 자동 체크)
```

### 2.4 STATE summary

```
S3-A         : FROZEN (Colab-only, v3 §4 carry)
PANEL        : ACTIVE
STEP 1       : LOCKED (v3)
STEP 2       : LOCKED (v3) + EXECUTED (본 세션) + SAVED
STEP 3       : LOCKED (v3) + EXECUTED (본 세션) + SAVED
STEP 4       : LOCKED (본 세션) + CODE UPLOADED + PENDING_EXEC
STEP 5       : PENDING (Ω tradeable region, ENTRY 신호 대기)
```

---

## 3. 데이터 layer (v3 §3 + 본 세션 산출 추가)

### 3.1 `state_vector/panel.parquet` (577,311 rows) — v3 carry

```
cols (18): date, code, close, p, r, sigma, v, l, flow,
           z_r, z_sigma, z_v, z_flow,
           bin_r, bin_sigma, bin_v, bin_flow, state_id
meta: 2015-04-27 ~ 2026-06-11, codes=261, states 0..1295 모두 점유

검증 (본 세션 [6/6]):
  rows  = 577,311  ✓ (v3 §3.1 일치)
  codes = 261      ✓
  dates = 2729     ✓
```

### 3.2 `observation/attribution.parquet` (5,593 rows) — v3 carry, 무변경

### 3.3 `backtest/h20_nonoverlap/trades.parquet` — v3 carry, 무변경

### 3.4 **NEW** `regime/` (본 세션 산출, Colab-only)

```
경로: /content/super/data/processed/regime/

regime.parquet      1,227,816 bytes
  cols: date, code, state_id, Z_t, R_t
  rows: 577,311 (panel 동일)
  Z_t ∈ {-1, 0..7}                                  sentinel -1 = invalid
  R_t ∈ {NaN, TREND, RANGE, SHOCK, TRANSITION}      NaN = invalid (Z_t=-1과 동치)

T_HMM.npy           640 bytes
  shape (8,8) float64, hmmlearn EM 산출 transition matrix
  diagnostic only — STEP 3에서 사용 금지 (S4-a §6.4)

label_map.json      2,448 bytes
  {z (0..7)} → label, scores, stationary π, params
```

### 3.5 **NEW** `transition/` (본 세션 산출, Colab-only)

```
경로: /content/super/data/processed/transition/

T.npy               shape (8,8) float64
  empirical transition matrix
  T[i,j] = C[i,j] / Σ_j C[i,j]    (observed)
  T[i,:] = 0-vector               (unobserved row, 본 세션은 0 row 없음)

C.npy               shape (8,8) int64
  raw count matrix (pooled across 261 assets)

meta.json
  {n_transitions, row_sums, diagonal_p_stay, sparsity_T, label_map, params}
```

### 3.6 **PENDING** `edge/` (STEP 4 실행 후 생성 예정)

```
경로: /content/super/data/processed/edge/

기대 산출:
  E_state.npy           (8,)   float64 (NaN allowed)
  E_transition.npy      (8,8)  float64 (NaN allowed)
  N_state.npy           (8,)   int64
  N_transition.npy      (8,8)  int64
  meta.json
```

---

## 4. S3-A 결과 (HANDOFF_v3 §4 그대로, 본 세션 미touch)

```
Colab-only:
  scripts/edge/build_ev_surface.py    (HANDOFF_v2 §5 코드)
  data/processed/edge/ev_surface.parquet
  reports/run_logs/D_ev_surface.log

⚠ 주의: STEP 4 산출 경로 `data/processed/edge/` 와 동일.
   S3-A artifact는 ev_surface.parquet이고, STEP 4는 E_state/E_transition .npy.
   파일명 다르므로 충돌 없음. 하지만 의미상 별도 layer임을 기억:
     • S3-A = observation projection (attribution → conditional mean)
     • STEP 4 = generative expected return (Z_t → forward log return)
   v3 §8 NOTE 참조.
```

---

## 5. STEP 1 — STATE VECTOR (LOCKED, v3 §5 그대로)

요약:
```
S_t          = (p, v, flow, sigma, l)
ORDERING     = INVARIANT
X_cont       ∈ ℝ^{T × N × 5}
Y_state      ∈ ℤ^{T × N}      (state_id, 0..1295)
K_bin = 6, K_feat = 5, N_state = 1296

r = Δp     DERIVED ONLY, STEP 3+ 사용 허용 (STEP 2 금지)
```

본 세션 변경: 없음.

---

## 6. STEP 2 — REGIME CLASSIFICATION (LOCKED + EXECUTED + SAVED)

### 6.1 SPEC — v3 §6 그대로 (본 세션 변경 없음)

PIPELINE / label_map / OUTPUT / HARD CONSTRAINTS / Resolution trace 전부 v3 §6 참조.

### 6.2 CODE — 본 세션 신규

```
파일       : scripts/regime/build_regime.py
크기       : 309 lines / 11,658 bytes
GitHub HEAD: c9e3072 (c46f9b8에서 build_reg.py 오타 정리됨)

매핑 (spec → code):
  §5.2 ORDERING (p,v,flow,sigma,l)         → FEATURES const
  §6.1 zscore W=252 per-asset shift(1)     → normalize() / _zscore()
  §6.1 valid_mask strict all-finite        → build_valid_mask()
  §6.1 k-means K=8,++/42,20,300,1e-4,L2    → KM_PARAMS / run_kmeans()
  §6.1 split-on-invalid                    → build_sequences()
  §6.1 CategoricalHMM(8,200,1e-3,EM,pool)  → HMM_PARAMS / fit_hmm()
  §6.1 π=uniform init → EM → stationary    → fit_hmm() + _stationary_or_uniform()
  §6.1 fallback uniform (reducible/period) → unit_count>1 OR pi<0 OR sum≈0
  §6.2 N10 decode ordering                  → decode_bin_r_sigma() (s%6, (s//6)%6)
  §6.2 dominance + score + tie-break       → compute_label_map()
```

### 6.3 N10 해소 (v3 §9 carry → 본 세션 RESOLVED)

```
scripts/build_state_vector.py line 70:
  sid = bin_r + 6·bin_sigma + 36·bin_v + 216·bin_flow

→ (b0, b1, b2, b3) = (bin_r, bin_sigma, bin_v, bin_flow)
→ decode:
    bin_r     =  s          % 6
    bin_sigma = (s //   6)  % 6
    bin_v     = (s //  36)  % 6
    bin_flow  = (s // 216)  % 6

INVARIANT 검증 ([14, 266, 606, 952]):
  14  = 2 + 6·2                                     ✓
  266 = 2 + 6·2 + 36·1 + 216·1                      ✓
  606 = 0 + 6·5 + 36·4 + 216·2                      ✓
  952 = 4 + 6·2 + 36·2 + 216·4                      ✓
```

### 6.4 ⚠ PATH BUG (본 세션 incident, GitHub 미수정)

```
증상   : 1차 dry-run 시 FileNotFoundError
  File "/content/super/scripts/regime/build_regime.py", line 57
  no state_vector parquet in /content/super/scripts/data/processed/state_vector
                                                ^^^^^^^ WRONG (한 단계 부족)

원인   : ROOT = dirname × 2  (잘못)
  build_state_vector.py는 scripts/ 직하 (depth 2) → dirname × 2 OK
  build_regime.py는    scripts/regime/ (depth 3) → dirname × 3 필요

수정   : ROOT = dirname × 3   (line 30)
  ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

적용   : Colab in-place sed (commit 없음)
  !sed -i 's|^ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))|ROOT     = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))|' /content/super/scripts/regime/build_regime.py

⚠ GitHub의 build_regime.py 는 여전히 BUGGY (dirname × 2)
  → Colab runtime 손실 후 재clone 시 BUG 다시 발생
  → 재실행 전 sed 재적용 필요 (§12 Step C 참조)

build_transition.py / build_edge.py: 사전 인지로 dirname × 3 적용됨 (GitHub correct)
```

### 6.5 EXECUTION RESULT (verify stdout, 본 세션)

```
[1/8] load_panel
      rows=577,311  codes=261  dates=2729
[2/8] normalize (W=252, per-asset, shift(1))
[3/8] valid_mask (strict all-finite, 5ch)
      valid rows : 512,336 / 577,311  (88.75%)
[4/8] k-means (K=8, seed=42, n_init=20)
      C_t counts :
        0:    92,099    1:    38,944    2:   109,397    3:    24,028
        4:    41,076    5:   106,641    6:        65    7:   100,086
[5/8] sequences (split-on-invalid, per-asset)
      sequences  : 260   obs: 512,336   min=9  max=2477  mean=1970.5
[6/8] CategoricalHMM (K=8, n_iter=200, EM, pooled)
      unit-modulus eigs : 1
      stationary π      : [0.2415, 0.1076, 0.0875, 0.0178, 0.0176, 0.3383, 0.0943, 0.0953]
      fallback uniform  : False
[7/8] predict Z_t
[8/8] label_map + R_t

=== VERIFY ===
invalid (-1)   : 64,975  (11.25%)
valid          : 512,336 (88.75%)
Z_t range      : [0, 7]
Z_t distrib    :
  0:123,033  1: 51,071  2: 47,999  3:  7,525
  4:  8,638  5:173,153  6: 50,596  7: 50,321
R_t distrib    :
  TRANSITION : 230,741
  SHOCK      : 173,153
  TREND      : 108,442
  RANGE      :       0     ← (관찰. dominance 분포의 자연 산물)
label_map      :
  {0:'TRANSITION', 1:'TRANSITION', 2:'TRANSITION', 3:'TREND',
   4:'TRANSITION', 5:'SHOCK', 6:'TREND', 7:'TREND'}
✅ Z_t=-1 ↔ R_t=NaN consistent
```

### 6.6 관찰 (FAIL 아님, spec 결과)

```
[O1] C_t cluster 6 = 65 obs (0.013%)
     → 거의 비어 있는 k-means cluster. HMM이 흡수.
     → spec 위반 아님 (K=8 LOCKED, 보정 금지).

[O2] R_t 분포에서 RANGE=0
     → label_map 어느 hidden state도 RANGE 미할당
     → 원인: §6.2 dominance 정의(bin_sigma∈{0,1})를 만족하는 state_id가
            전체 distribution에서 trend_dominant보다 작음
     → 데이터 분포의 자연 산물, 보정 금지

[O3] label 분포 skew (TRANSITION 45%, SHOCK 34%, TREND 21%, RANGE 0%)
     → STEP 4 EDGE FIELD에서 +EV 영역 식별 시 자연 필터링
     → STEP 5 (Ω 추출)에서 결정
```

---

## 7. STEP 3 — TRANSITION ESTIMATION (LOCKED + EXECUTED + SAVED)

### 7.1 SPEC — v3 §7 그대로

INPUT contract / PROCEDURE / OUTPUT / HARD CONSTRAINTS 전부 v3 §7 참조.

### 7.2 CODE — 본 세션 신규

```
파일       : scripts/transition/build_transition.py
크기       : 192 lines / 6,702 bytes
GitHub HEAD: 28cbb0c (Updating c46f9b8..28cbb0c)
ROOT       : dirname × 3 (사전 적용, BUG 없음)

매핑:
  §7.1 INPUT (Z_t only)                    → load_regime() columns=["date","code","Z_t"]
  §7.2 same code + sentinel(-1) 검사       → groupby + shift(-1) + .notna() + != -1
  §7.2 pooled C[i,j] count                 → np.add.at(C, (curr, next), 1)
  §7.2 row-normalize                       → T[i] = C[i]/row_sums[i] if >0
  §7.2 zero-row → 0-vector                 → np.zeros init, observed rows만 채움
  §7.3 property assertion                  → abs(s-1)<1e-9 또는 s==0
  §7.4 T_HMM 미사용                        → load 자체 안 함
  §7.4 feature/state 미사용                → Z_t 외 어떤 column도 미사용
  Q3-(b) 해석                              → sentinel + same-code 검사만으로 subseq 식별
```

### 7.3 EXECUTION RESULT (verify stdout)

```
n_transitions  : 512,076   (= Z_t!=-1 인 row 중 마지막 row 261개 제외 ≈ 512,075)

C row sums     : [122,957, 51,054, 47,987, 7,525, 8,638, 173,024, 50,576, 50,315]
                  (= STEP 2 Z_t distrib - 자산당 terminal row 1개씩 ≈ 260개 차이)
C col sums     : [122,951, 51,041, 47,974, 7,519, 8,638, 173,088, 50,569, 50,296]
observed rows  : 8 / 8      (zero-row 없음)

T row sums     : [1, 1, 1, 1, 1, 1, 1, 1]   ✓
T value range  : [0.0, 1.0]
diagonal       : [0.9446, 0.0006, 0.0000, 0.0053, 0.1896, 0.9635, 0.0000, 0.0000]
mean p_stay    : 0.2630

T matrix:
       j=0      j=1      j=2      j=3      j=4      j=5      j=6      j=7    label
  i=0  0.9446   0.0022   0.0025   0.0000   0.0373   0.0000   0.0134   0.0000  TRANSITION
  i=1  0.0202   0.0006   0.8792   0.0000   0.0434   0.0002   0.0563   0.0000  TRANSITION
  i=2  0.0000   1.0000   0.0000   0.0000   0.0000   0.0000   0.0000   0.0000  TRANSITION
  i=3  0.2074   0.1850   0.1466   0.0053   0.0255   0.0000   0.0000   0.4302  TREND
  i=4  0.0000   0.0361   0.0372   0.0000   0.1896   0.7371   0.0000   0.0000  TRANSITION
  i=5  0.0242   0.0061   0.0062   0.0000   0.0000   0.9635   0.0000   0.0000  SHOCK
  i=6  0.0000   0.0000   0.0000   0.0695   0.0000   0.0000   0.0000   0.9304  TREND
  i=7  0.0005   0.0000   0.0056   0.0787   0.0000   0.0000   0.9152   0.0000  TREND

✅ properties: T[i,j]≥0, Σ_j T[i,j] ∈ {0,1}
```

### 7.4 구조적 관찰 (다음 단계 EV 해석 참고용)

```
[ATTRACTORS] sticky high-mass self-transition
  i=0 (TRANSITION) : p_stay=0.9446, count=122,957
  i=5 (SHOCK)      : p_stay=0.9635, count=173,024

[2-CYCLES] lag-1 oscillators (period 2)
  Cycle A : (1↔2) TRANSITION/TRANSITION
    1→2 = 0.8792 (44,889)    2→1 = 1.0000 (47,987)
    p_stay(1)=0.0006, p_stay(2)=0.0000
  Cycle B : (6↔7) TREND/TREND
    6→7 = 0.9304 (47,058)    7→6 = 0.9152 (46,049)
    p_stay(6)=0.0000, p_stay(7)=0.0000

[BRIDGES] low-mass dispersive
  i=3 (TREND,       7,525)  : 3→7=0.43, 3→0=0.21, 3→1=0.19, 3→2=0.15
  i=4 (TRANSITION,  8,638)  : 4→5=0.74, 4→4=0.19

[TOPOLOGY]
  attractor 0 ←→ cycle (1,2) ←→ bridge 3 ←→ cycle (6,7)
                                              ↑
  attractor 5 ← bridge 4 ───────────────────┘
```

---

## 8. STEP 4 — EDGE FIELD (LOCKED + CODE UPLOADED + PENDING EXEC)

### 8.1 SPEC LOCK (본 세션 신규 — id="n7x4qp" + id="n11_estate_inclusion")

```
DEFINITIONS:
  r_t              := p_{t+1} - p_t             (p = log(close); Δp = log return)
  E_state[i]       := E[r_t | Z_t = i]          (β SYMMETRIC inclusion)
  E_transition[i,j]:= E[r_t | Z_t = i, Z_{t+1} = j]

INCLUSION (β SYMMETRIC):
  valid pair iff:
    Z_t != -1
    Z_{t+1} != -1
    r_t notna (= next-row exists in same code)
  → STEP 3 valid 조건과 정확히 동일
  → 결과: E_state[i] ≡ Σ_j T[i,j] · E_transition[i,j]  (algebraic identity)

MISSING CELL: N14 = NaN (no fill, no smoothing, no interpolation)

HARD CONSTRAINTS:
  • return 계산 외 feature 사용 금지
  • smoothing / clipping / winsorizing 금지
  • regime 기반 필터링 사전 적용 금지
  • negative EV 포함 상태 임의 제거 금지
  • 미관측 cell → NaN
```

### 8.2 Resolution trace (lock 도달 경로)

```
1차 ambiguity (id="n7x4qp_r_convention"):
  (A) contemporaneous  r_t = p_t - p_{t-1}    descriptive only
  (B) forward          r_t = p_{t+1} - p_t    predictive EV  ← SELECT
  근거: STEP 5 (Ω 추출)에 forward EV가 필요. (6↔7) cycle directional asymmetry.

2차 ambiguity 4건 (id="n11_estate_inclusion" / "resolve_4_items"):
  N11 (E_state inclusion):
    (α) PURE        Z_{t+1} ∈ {-1, 0..7}        descriptive
    (β) SYMMETRIC   Z_{t+1} ∈ {0..7} only       ← SELECT
    근거: framework consistency (E_state ≡ Σ T·E_trans)

  N12 (price source):
    panel.parquet merge on (date, code)         ← SELECT (대안 없음)

  N13 (return definition):
    log return = p_{t+1} - p_t (where p = log(close))  ← SELECT
    (사용자 표기 "r_t = log(p_{t+1}) - log(p_t)" 의 정합 해석:
     p가 close가 아니라 log(close) 컬럼임을 감안하면 r_t = panel.p_{t+1} - panel.p_t)

  N14 (missing cell):
    (a) NaN       ← SELECT (no fill 원칙)
    (b) 0           rejected (distortion)
```

### 8.3 CODE — 본 세션 신규, GitHub 업로드 완료

```
파일       : scripts/edge/build_edge.py
크기       : 289 lines / (size 미확인, GitHub에서 확인 가능)
GitHub HEAD: (build_edge.py upload commit, hash 미확인)
ROOT       : dirname × 3 (사전 적용, BUG 없음)

매핑 (spec → code):
  n7x4qp (forward)        → df.groupby(code).p.shift(-1) - p
  n11 (β SYMMETRIC)       → mask: Z_t≠-1 ∧ Z_next.notna() ∧ Z_next≠-1 ∧ r_t.notna()
  N12 (panel merge)       → load_merged() inner-join on (date, code)
  N13 (log return)        → 직접 p_{t+1} - p_t (p가 이미 log(close))
  N14 (NaN unobserved)    → np.full(..., np.nan), no fill
  algebraic identity      → identity_check() 자동 assertion (max |Δ| < 1e-9)

OUTPUT 경로 (실행 후 산출 예정):
  data/processed/edge/E_state.npy       (8,)   float64 NaN allowed
  data/processed/edge/E_transition.npy  (8,8)  float64 NaN allowed
  data/processed/edge/N_state.npy       (8,)   int64
  data/processed/edge/N_transition.npy  (8,8)  int64
  data/processed/edge/meta.json
```

### 8.4 사전 검증 (Claude local syntax + identity 미니 시뮬레이션)

```
syntax OK
ROOT path OK (scripts/edge/ → /content/super)
identity check OK (4×4 미니 표본, Δ = 0.00e+00)
```

### 8.5 EXECUTION STATUS

```
PENDING:
  Colab에서 git pull 미실행 → build_edge.py 미반영
  dry-run 미실행
  save 미실행

기대 결과 (실행 시 예상):
  n_valid pairs = 512,076  (STEP 3 n_transitions와 동일해야 함)
  identity 자동 PASS (β의 직접 귀결)
  추정 시간 : <2초
```

---

## 9. 미해결 / pending 항목 (FAIL 아님, 실행 단계)

```
[STEP 4 EXEC]    Colab에서:
                   !cd /content/super && git pull
                   !python scripts/edge/build_edge.py --dry-run
                   !python scripts/edge/build_edge.py            (--dry-run 검증 후)

[STEP 5 ENTRY]   "STEP 5 START" 또는 "STEP 5 CODE" 명시 신호 대기
                 §8 carry: Ω = tradeable region extraction
                 입력 후보: E_state, E_transition, T, label_map, MIN_VISITS, T_THRESHOLD
                 spec entry block 사용자 명시 필요

[COMMIT 분기]    data/processed/{regime, transition, edge} GitHub 반영 여부
                 → 사용자 결정 대기 (§14)
                 → Colab runtime 손실 위험 회피 시 commit 필요

[BUG-1 영구 수정] scripts/regime/build_regime.py GitHub 파일의 ROOT BUG
                 sed 패치를 commit으로 영구 반영 필요 (선택)
                 ※ 현 Colab은 sed 적용된 상태 (runtime 유지 시 정상)
```

### 9.1 v3 §9 pending 처리 현황

```
[N10]    RESOLVED (§6.3) — (b0..b3) = (bin_r, bin_sigma, bin_v, bin_flow)
[Q3]     RESOLVED — (b) sentinel(-1) + same-code 검사로 subseq 식별 (build_transition.py)
[S5-a]   RESOLVED — compute_label_map() 내 P_z(s) 계산이 (regime × state_id) 4×1296 의미 내포
[Q-OUT]  RESOLVED — _stationary_or_uniform() custom post-processing 구현
```

---

## 10. LOCKS (v3 §10 그대로, INTACT)

```
[L1] 추측 금지
[L2] 자동 채움 금지
[L3] LOCKED kernel 무수정
     scripts/build_state_vector.py, scripts/build_transition.py (기존 kernel),
     scripts/backtest_nonoverlap.py, scripts/observation/* 전부
     ※ §14 UNLOCK SPEC에 의해 PARTIAL READ-ONLY 허용 (write·commit 여전히 금지)
     ※ 본 세션 신규 추가 scripts/regime/, scripts/transition/, scripts/edge/ 는
        L3 보호 범위 외 (본 세션 산출물)
[L4] §5.2 unlock signal 없이 STAGE 3 작업 금지 (S3-A 이미 충족)
[L5] observation/* schema 변경 금지 (8 attr keys, 5 drift keys, panel 18 cols)
[L6] 자동 git commit/push 금지
[L7] 사용자 환경 추정 금지
[L8] read-only inspection 항상 허용
[L9] 실패 시 STOP, 자동 retry 금지
```

---

## 11. 사용자 상호작용 패턴 (v3 §11 carry + 본 세션 관찰)

### 11.1 본 세션에서 사용된 unlock signals (자연어 아님)

```
"STEP 2 CODE"           → PHASE 1 unlock (id="trigger_block")
"STEP 3 CODE"           → STEP 3 entry (id="kz3a1p")
"STEP 4 START"          → STEP 4 spec entry (id="n7x4qp")
"SELECT = (B)"          → r_t convention lock
"N11 = (β)" 외 3건       → 4-item resolve
```

### 11.2 자연어 진입 거부 사례 (본 세션 실제)

```
사용자: "실행"
Claude: PHASE 0 (정독 + VALIDATION REPORT)으로 해석 종료.
        PHASE 1은 "STEP 2 CODE" 외 진입 금지.

사용자: "시작하라"
Claude: STOP. §11 위반 방지: 자연어 unlock signal 아님. 거부.
        필요 입력: HANDOFF_v3.md 본문 paste / 첨부 / raw URL.
```

### 11.3 form 명시

```
* STEP / * INPUT / * TRANSFORMATION / * OUTPUT / * NEXT STEP
id="..." 태그
SELECT = (α) / (β) / (a) / (b) ... 단일 선택
HARD CONSTRAINT LOCK / EXECUTION CONSTRAINT
══════════════════════════════════════════════════════════════
```

새 세션도 이 형식 사용 예상. 명시값(SELECT=..., id 태그) 있는지 확인.

---

## 12. 다음 세션 첫 동작 (반드시 이 순서)

### Step A) Colab 환경 보존 여부 확인

```
같은 Colab runtime 유지:
  → /content/super 안의 신규 파일 그대로
  → data/processed/{regime, transition} 산출물 보존
  → build_regime.py 의 sed-applied 상태 보존
  → STEP 4 dry-run 즉시 가능

새 노트북 / runtime 끊김:
  → setup cell 재실행 (§12 Step C)
  → data/processed/{regime, transition} 소실
  → build_regime.py 의 PATH BUG 다시 발생 → sed 재적용 필수
  → STEP 2, STEP 3 재실행 필요 (총 ~10분)
  → 그 후 STEP 4 dry-run
```

### Step B) 본 인계서(HANDOFF_v4) 정독

```
필수 정독: §0, §2, §3.4~3.6, §6.4(PATH BUG), §8, §9
선택 정독: §5, §7, §11, §13~17
```

### Step C) Setup cell (paste & run)

```python
# === SUPER — STEP 4 execution setup (HANDOFF v4 §12 Step C) ===
import os, sys, subprocess, pathlib

REPO_HOST = "github.com/stanleyim/super.git"
REPO_PATH = "/content/super"

# --- [1/7] GH_TOKEN ---
if "GH_TOKEN" not in os.environ:
    try:
        from google.colab import userdata
        os.environ["GH_TOKEN"] = userdata.get("GH_TOKEN")
    except Exception as e:
        sys.exit(f"ABORT: GH_TOKEN load fail: {type(e).__name__}: {e}")
token = os.environ.get("GH_TOKEN")
if not token:
    sys.exit("ABORT: GH_TOKEN empty")
print(f"[1/7] GH_TOKEN loaded (len={len(token)})")

# --- [2/7] clone or pull ---
if not os.path.isdir(REPO_PATH):
    r = subprocess.run(
        ["git", "clone", f"https://x-access-token:{token}@{REPO_HOST}", REPO_PATH],
        capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ABORT: clone failed\n{r.stderr.replace(token, '***')}")
    print(f"[2/7] cloned   → {REPO_PATH}")
    fresh_clone = True
else:
    os.chdir(REPO_PATH)
    r = subprocess.run(["git", "pull", "--ff-only"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ABORT: pull failed\n{r.stderr.replace(token, '***')}")
    tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "(up to date)"
    print(f"[2/7] pulled   → {REPO_PATH}  | {tail}")
    fresh_clone = False
os.chdir(REPO_PATH)

# --- [3/7] HEAD verification ---
print("\n[3/7] HEAD")
for cmd in (["git", "log", "--oneline", "-10"], ["git", "rev-parse", "HEAD"]):
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = r.stdout.strip().replace("\n", "\n      ")
    print(f"      $ {' '.join(cmd)}\n      {out}")

# --- [4/7] dependencies ---
print("\n[4/7] dependencies")
r = subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q",
     "scikit-learn", "hmmlearn", "--break-system-packages"],
    capture_output=True, text=True)
print(f"      pip exit={r.returncode}")
if r.returncode != 0:
    print(f"      stderr (tail): {r.stderr[-500:]}")
    sys.exit("ABORT: dependency install failed")
import sklearn, hmmlearn, numpy, pandas
print(f"      sklearn  : {sklearn.__version__}    (expected 1.6.x)")
print(f"      hmmlearn : {hmmlearn.__version__}    (expected 0.3.x)")
print(f"      numpy    : {numpy.__version__}")
print(f"      pandas   : {pandas.__version__}")

# --- [5/7] BUG-1 patch (build_regime.py ROOT depth)  ※ fresh clone 시 필수 ---
print("\n[5/7] build_regime.py PATH BUG patch")
reg_path = pathlib.Path("scripts/regime/build_regime.py")
if reg_path.exists():
    content = reg_path.read_text()
    buggy   = "ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))"
    fixed   = "ROOT     = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))"
    if buggy in content and fixed not in content:
        reg_path.write_text(content.replace(buggy, fixed))
        print(f"      ✅ patched  (dirname×2 → dirname×3)")
    elif fixed in content:
        print(f"      already fixed")
    else:
        print(f"      ⚠ unexpected ROOT pattern — 수동 확인 필요")
else:
    print(f"      (not present)")

# --- [6/7] script inventory ---
print("\n[6/7] scripts/* inventory")
for p in ["scripts/regime/build_regime.py",
          "scripts/transition/build_transition.py",
          "scripts/edge/build_edge.py"]:
    pp = pathlib.Path(p)
    print(f"      {p:50s} {'(' + str(pp.stat().st_size) + ' bytes)' if pp.exists() else '✗ missing'}")

# --- [7/7] data/processed inventory ---
print("\n[7/7] data/processed/* inventory")
for d in ["state_vector", "regime", "transition", "edge"]:
    dd = pathlib.Path(f"data/processed/{d}")
    print(f"      data/processed/{d:20s}", end=" ")
    if not dd.exists():
        print("✗ missing")
        continue
    items = sorted(dd.iterdir())
    if not items:
        print("(empty)")
        continue
    for it in items:
        sz = it.stat().st_size if it.is_file() else "-"
        print(f"\n        {it.name:30s}  {sz}", end="")
    print()

print("\n✅ setup complete")
```

### Step D) HEAD drift 판정

```
기대 (정상):
  • HEAD = build_edge.py upload commit 이후
  • 본 세션 인계 후 사용자가 commit한 추가 변경 있을 수 있음 (HANDOFF_v4 등)
  • scripts/regime/build_regime.py 변경 0 (BUG 그대로) → §12 [5/7] patch가 자동 처리
  • 사용자가 본 세션 후 build_regime.py 영구 수정 commit 한 경우 → patch가 already fixed 처리

이상:
  • LOCKED kernel (L3 protected) 변경 → STOP, L3 위반 보고
  • observation schema 변경 → STOP, L5 위반 보고

drift 정상 시 진입.
```

### Step E) STEP 4 dry-run → save → STEP 5 entry 대기

```
같은 runtime (Step A 상황 1):
  1) !python scripts/edge/build_edge.py --dry-run
  2) verify 결과 + identity check PASS 확인
  3) !python scripts/edge/build_edge.py        (save)
  4) "STEP 5 START" 명시 신호 대기

새 runtime (Step A 상황 2):
  1) STEP 2 재실행:
     !python scripts/regime/build_regime.py
     (k-means + HMM, ~5~15분)
  2) STEP 3 재실행:
     !python scripts/transition/build_transition.py
     (<1초)
  3) STEP 4 dry-run + save (위 1~3과 동일)
  4) "STEP 5 START" 신호 대기
```

### Step F) 진입 신호 (§5.2 unlock signal, 자연어 거부)

```
(i)  "STEP 4 EXEC"        → dry-run + save (해당 진입 신호도 필요)
(ii) "STEP 5 START"       → Ω tradeable region spec entry
(iii) "STEP 5 CODE"       → STEP 5 spec LOCK 후 코드 작성 (STEP 5 spec 미확정 시 ENTRY 선행)
(iv) 기타 명시 (분기, 재정의 등)

금지:
  • 자연어 동의로 진입 판정 금지 (§11.2)
  • 자동 다음 STEP 진행 금지 (L1, L4)
```

---

## 13. 환경 의존성 (본 세션 검증된 버전)

```
Python      : Colab default (3.x, 정확 버전 미기록)
pyarrow     : Colab default
scikit-learn: 1.6.1    ✓ KMeans, k-means++ 호환
hmmlearn    : 0.3.3    ✓ CategoricalHMM 호환
numpy       : 2.0.2
pandas      : 2.2.2

설치 (필요 시):
  pip install scikit-learn hmmlearn --break-system-packages -q

실행 시간 측정 (본 세션):
  STEP 2 (build_regime.py, 577K rows)  : 약 5분 (k-means n_init=20 + HMM n_iter=200)
  STEP 3 (build_transition.py)         : <1초
  STEP 4 (build_edge.py, 예상)         : <2초
```

---

## 14. 미실행 / 유보 항목

```
- STEP 4 dry-run + save (Step E, 다음 세션 첫 작업)
- STEP 5 (Ω tradeable region) spec entry
- COMMIT 분기:
    • data/processed/{regime, transition, edge}/* GitHub 반영 여부
    • scripts/regime/build_regime.py PATH BUG 영구 수정 commit 여부
    • HANDOFF_v4.md 자체 commit
- S3-B (tradeable mask) — 별도 §5.2 unlock signal 필요 (v2 §6 그대로)
- S3-C, S3-D — 별도 unlock 필요
```

---

## 15. 핵심 risk

### 15.1 Colab runtime 손실

```
손실 시 영향:
  • data/processed/regime/      → 소실 (재실행 ~5분)
  • data/processed/transition/  → 소실 (재실행 <1초)
  • build_regime.py PATH BUG    → 재발 (sed 재적용 필요 ← §12 [5/7] 자동화됨)

회피:
  • 새 세션 첫 작업으로 data artifacts commit (사용자 결정)
  • 또는 §12 setup cell의 [5/7] 자동 patch에 의존
```

### 15.2 STEP 4 미실행

```
현재 GitHub에 build_edge.py 업로드 완료, but:
  • Colab 미pull
  • dry-run 미실행
  • save 미실행
  → data/processed/edge/ 미생성

영향:
  • STEP 5 (Ω 추출) 입력 부재
  • 다음 세션 첫 작업으로 처리 (§12 Step E)
```

### 15.3 ⚠ build_regime.py PATH BUG (GitHub 미수정)

```
GitHub의 scripts/regime/build_regime.py line 30:
  ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   ← BUGGY

Colab의 동 파일은 sed-fixed:
  ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   ← OK

대응:
  • runtime 유지 → 영향 없음
  • runtime 손실 → re-clone 시 BUG 재발 → §12 setup cell [5/7] 자동 patch
  • 영구 수정 권장: 사용자가 GitHub에 fixed 버전 commit

build_transition.py / build_edge.py: dirname×3 사전 적용됨, BUG 없음.
```

### 15.4 spec drift (v3 §15.2 carry)

```
STEP 1/2/3/4 SPEC은 본 인계서 (v4) + v3에 완전 기록됨.
runtime 손실되어도 spec은 재구성 가능.

특히 STEP 4의 미세 명시값:
  • r_t convention (forward, log return)
  • β SYMMETRIC inclusion
  • NaN unobserved
  • identity check tolerance 1e-9
  → §8.1 / §8.2 / §2.3 참조
```

### 15.5 사용자 상호작용 패턴 망각 (v3 §15.3 carry)

```
자연어 "진행", "실행", "go", "시작하라" → unlock signal 아님.
명시값 (SELECT=, id="...", "STEP N CODE" 등)만 진입 트리거.
§11 정독 필수.
```

---

## 16. 검증된 fact 요약 (참조용)

### 16.1 v3 carry

```
NEXT_SESSION.md §1.4 Sharpe 1.806 / Calmar 2.473 / MDD -22.96%
INVARIANT states = [14, 266, 606, 952]
trades = attribution rows = 5,593
panel = 12 yearly union (diff=0), 577,311 rows
net mean = 0.04609, gross mean = 0.04909, gap = cost_rt = 0.003
S3-A diagnostics: 84 obs cells / sparsity 0.9676 / pass_both=13
```

### 16.2 본 세션 신규

```
[panel 정합성 재확인]
  rows  = 577,311
  codes = 261
  dates = 2729  (2015-04-27 ~ 2026-06-11)

[STEP 2 verify]
  valid rows = 512,336  (88.75%)
  invalid    =  64,975  (11.25%)
  sequences  =     260   (asset 261 중 1개 누락 가능성, valid 없는 asset)
  obs        = 512,336
  seq_min=9, seq_max=2477, seq_mean=1970.5

  C_t cluster sizes:
    0:  92099   1:  38944   2: 109397   3:  24028
    4:  41076   5: 106641   6:     65   7: 100086

  Z_t hidden state sizes:
    0: 123033   1:  51071   2:  47999   3:   7525
    4:   8638   5: 173153   6:  50596   7:  50321

  R_t (8→4 label_map):
    TRANSITION = 230741 (45.0%)
    SHOCK      = 173153 (33.8%)
    TREND      = 108442 (21.2%)
    RANGE      =      0  (0.0%)

  label_map:
    z=0 → TRANSITION   z=1 → TRANSITION   z=2 → TRANSITION   z=3 → TREND
    z=4 → TRANSITION   z=5 → SHOCK        z=6 → TREND        z=7 → TREND

  HMM stationary π:
    [0.2415, 0.1076, 0.0875, 0.0178, 0.0176, 0.3383, 0.0943, 0.0953]
  unit-modulus eigs = 1 (irreducible)
  fallback uniform = False

[STEP 3 verify]
  n_transitions = 512,076
  T row sums    = [1,1,1,1,1,1,1,1]   (8/8 observed)
  T diagonal    = [0.9446, 0.0006, 0.0000, 0.0053, 0.1896, 0.9635, 0.0000, 0.0000]
  mean p_stay   = 0.2630
  zero-rows     = 0

  topology:
    attractors : i=0 (TRANSITION), i=5 (SHOCK)
    2-cycles   : (1↔2) TRANSITION/TRANSITION, (6↔7) TREND/TREND
    bridges    : i=3 (TREND → 7/0/1/2 dispersive), i=4 (TRANSITION → 5 dominant)
```

### 16.3 STEP 4 사전 예상 (실행 후 검증 항목)

```
n_valid_pairs (expected) : 512,076   (= STEP 3 n_transitions, β SYMMETRIC 의 직접 귀결)
N_state sum  (expected)  : 512,076
N_trans sum  (expected)  : 512,076
observed_states          : 8 (모든 hidden state populated)
observed_trans           : (C.npy 의 nonzero 셀 수 = N_trans nonzero 셀 수)

identity check (expected): max |Δ| < 1e-9
```

---

## 17. 본 세션 대화 흐름 요약 (참조용)

```
1. HANDOFF_v3.md fetch 시도 → search 거부 → screenshot으로 public 확인 → upload 수신 → 정독
2. VALIDATION REPORT: PASS (§5/§6/§7/§9/§10/§12 모두 인지)
3. EXECUTION ENTRY PROTOCOL 수신 (PHASE 0~5)
4. "STEP 2 CODE" trigger 수신
5. N10 해소: scripts/build_state_vector.py L3 read
              → (b0..b3) = (bin_r, bin_sigma, bin_v, bin_flow)
              → INVARIANT states 산식 검증 ✓
6. build_regime.py 작성 (309 lines)
7. setup cell 실행 → HEAD c46f9b8 정상 → deps 확인
8. dry-run 시도 → FileNotFoundError (PATH BUG 발견)
9. sed in-place patch (ROOT dirname × 2 → × 3)
10. dry-run 성공 → verify PASS (RANGE=0 관찰)
11. 정식 실행 → data/processed/regime/{regime.parquet, T_HMM.npy, label_map.json} 저장
12. "STEP 3 CODE" trigger
13. build_transition.py 작성 (192 lines)
    GitHub 업로드 → !git pull → HEAD 28cbb0c
14. dry-run → verify PASS (n_trans=512,076, 8/8 observed, topology 식별)
15. 정식 실행 → data/processed/transition/{T.npy, C.npy, meta.json} 저장
16. "STEP 4 START" + spec lock 요청
17. id="n7x4qp_r_convention" → SELECT (B) FORWARD
18. id="n11_estate_inclusion" + N12/N13/N14 → β / panel merge / log return / NaN
19. build_edge.py 작성 (289 lines), identity 미니 시뮬레이션 PASS
    GitHub 업로드 완료
20. !git pull + dry-run = 미실행 (사용자 시간 부족)
21. HANDOFF_v4 작성 (본 인계서)
```

---

```
STATE:    HANDOFF READY (v4)
HEAD:     build_edge.py upload commit (hash 미확인)
LOCKS:    INTACT (L1-L9, L3 partial-read)
STEPS:    1·2·3 LOCKED + EXECUTED + SAVED
          4 LOCKED + CODE UPLOADED + PENDING_EXEC
          5 PENDING (ENTRY 신호 대기)
EXEC:     STEP 4 dry-run + save 가 다음 세션 첫 작업
RISK:     build_regime.py GitHub PATH BUG (Colab sed-fixed only)
          data/processed/{regime, transition} Colab-only (commit 미반영)
```

**STATUS: SUSPENDED — 새 세션 진입 대기.**
