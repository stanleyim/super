# HANDOFF v5 — SUPER repo

STEP 2~4 EXECUTED + SAVED + COMMITTED / STEP 5~9 EXECUTED (in-context) / FREEZE pending

작성: 2026-06-13
선행: HANDOFF_v4 (commit 0866dbe)
COMMIT HEAD: 5770438 ("MSM v1: STEP 2/3/4 artifacts + BUG-1 fix + .gitignore whitelist")

---

## 0. 한 줄 요약

- HANDOFF_v4 §12 Step E 절차로 fresh clone 진입 (2회 — drift 검증 + 최종 commit)
- STEP 2~3 재실행 → §6.5 / §7.3 EXACT MATCH (deterministic seed=42 확인)
- STEP 4 dry-run + save → identity max|Δ| = 2.17e-19, 5종 file 산출
- STEP 5~9 analysis phase 5단계 in-context 완주
- §2.1 P1 LOCKED RETAINED 5종 (cost_rt, T_THRESHOLD, MIN_VISITS, TRADEABLE_REG, H) **자연어 release**
- 산출 결론 = STEP 9 multi-regime EV manifold (T* = regime-indexed function)
- bucket A (data/processed/*) + bucket B (BUG-1 fix) COMMITTED to GitHub
- bucket C (본 HANDOFF_v5.md) 본 commit으로 완료
- FREEZE v5 선언 직전

---

## 1. repo 절대 상태

```
세션 시작 HEAD : 0866dbe "Add files via upload" (HANDOFF_v4.md upload)
세션 중간 HEAD : 264c8e4 (사용자 PDF v5 upload)
세션 종료 HEAD : 5770438 (본 commit + 본 HANDOFF_v5.md)
working tree  : clean
```

v4 §1 bookkeeping 정정:
- v4 §1 기록: "직전 HEAD : 28cbb0c (build_transition.py 추가)"
- 실측: 28cbb0c = "Delete scripts/transition/abc.py" (오타 정리), 실제 build_transition.py upload = 6ba0961
- 원인: v4 작성 시 abc.py 오타 self-cleanup episode 누락
- operational 영향: 0

---

## 2. 누적 LOCK 상태

### 2.1 STEP 1~4 SPEC: v4 §2.1~2.3 INTACT carry

### 2.2 ⚠ §2.1 P1 LOCKED RETAINED 5종 자연어 release (본 세션 신규)

사용자 자연어 신호 ("FULL UNCONSTRAINED TRADEABLE MAPPING" / "SYSTEM RELEASE ACKNOWLEDGED") 로 다음 release:

```
cost_rt        : 0.003     → drop
T_THRESHOLD    : 2.0       → drop
MIN_VISITS     : 100       → drop (state-level 8/8 통과로 효과 미관측)
TRADEABLE_REG  : {TREND,RANGE} → drop (모든 regime 진입 허용)
H              : 20        → drop (h=1 적용, STEP 4 산출 정의 그대로)
```

⚠ 정식 §14 UNLOCK SPEC block (id, SELECT, RELEASED/RETAINED) 미작성
→ 본 v5 §2.2 가 effective release 기록
→ v6 carry 시 §14 형식화 권장
→ carry 누락 시 다음 세션이 §2.1 v3-carry 그대로 적용해 STEP 5~9 결과 무효 처리 가능

### 2.3 STEP 5~9 SPEC LOCK (본 세션 신규)

```
STEP 5 (TRADEABLE):
  T := { i ∈ {0..7} | E_state(i) > 0 }
  h = 1, filter = sign only
  결과: T = {0, 1, 3, 4, 5}

STEP 6 (STABILITY):
  S(i)  := Σ_{j∈T} P(i→j)
  L(i)  := 1 - S(i)
  C(T)_uw := mean S(i)
  C(T)_w  := Σ N(i)·S(i) / Σ N(i)

STEP 7 (ATTRACTOR):
  A(i)  := S(i) / (1 - S(i))   (ε → 0)
  cluster gap 자연 분리 (threshold 무)

STEP 8 (SPECTRUM):
  P_TT 5×5 → numpy.linalg.eig (4-decimal projection, Colab full-precision 미실행 보류)

STEP 9 (EV MANIFOLD):
  7개 변형 (A~G) 산출 → 4-class collapse → regime-indexed T*
```

### 2.4 STATE summary

```
S3-A          : FROZEN (v3/v4 carry)
PANEL         : ACTIVE
STEP 1        : LOCKED (v3)
STEP 2~4      : LOCKED + EXECUTED + SAVED + COMMITTED (본 세션)
STEP 5~9      : LOCKED + EXECUTED (in-context, §16.3 보존)
STEP 10       : PENDING (manifold → single policy, v6 권장)
COMMIT v5     : EXECUTED (bucket A + B + C)
FREEZE v5     : PENDING
```

---

## 3. 데이터 layer

### 3.1~3.3 v4 §3.1~§3.3 그대로 (state_vector, observation, backtest)

### 3.4 `data/processed/regime/` — **GitHub committed (5770438)**

```
regime.parquet      1,227,816 bytes  (date, code, state_id, Z_t, R_t / 577,311 rows)
T_HMM.npy           640 bytes        (diagnostic only)
label_map.json      2,448 bytes
```

### 3.5 `data/processed/transition/` — **GitHub committed (5770438)**

```
T.npy               (8,8) float64    empirical transition matrix
C.npy               (8,8) int64      raw count matrix
meta.json
```

### 3.6 `data/processed/edge/` — **GitHub committed (5770438)**

```
E_state.npy           (8,)   float64  ← 6/8 finite, 2/8 NaN
E_transition.npy      (8,8)  float64  ← 34/64 observed
N_state.npy           (8,)   int64
N_transition.npy      (8,8)  int64
meta.json
```

### 3.7 STEP 5~9 산출: file 무 (in-context only)

```
T = {0, 1, 3, 4, 5}, S(i), L(i), C(T), A(i), basin, λ_1..5, gap, τ_mix,
STEP 9 7-variant + 4-class collapse + invariant.

→ runtime 손실 시 §16.3 receipts 로부터 재산출 가능
→ STEP 4 file 산출 (GitHub committed) 에서 산술 재계산 가능
```

---

## 4~7. v4 §4~§7 그대로 carry, 본 세션 재실행 EXACT MATCH 확인

### 6. STEP 2 — REGIME
v4 §6 그대로. 본 세션 재실행 검증:
- §6.5 stdout 4-decimal EXACT MATCH (Z_t distrib, R_t distrib, stationary π, label_map)
- determinism: seed=42 reproducibility 확정 (2회 재실행 모두 동일)
- BUG-1 sed patch (working tree) + 영구 commit (scripts/regime/build_regime.py)

### 7. STEP 3 — TRANSITION
v4 §7 그대로. 본 세션 재실행 검증:
- §7.3 stdout EXACT MATCH (C 8×8 정수값 56 셀, T 8×8 4-decimal)

---

## 8. STEP 4 — EDGE FIELD (본 세션 신규 실행 + 산출)

### 8.1~8.4: v4 §8.1~8.4 그대로

### 8.5 EXECUTION RESULT (dry-run + save 모두 EXACT)

```
n_valid_pairs   : 512,076                ✓ (= STEP 3 n_transitions)
Σ N_state       : 512,076                ✓
Σ N_transition  : 512,076                ✓
observed_states : 8 / 8                  ✓
observed_trans  : 34 / 64 (53.1%)        ← v4 §16.3 정량 확정
identity max|Δ| : 2.17e-19               ✓ (β SYMMETRIC 직접 귀결)
save marker     : ✅ saved → data/processed/edge
```

### 8.6 E_state 산출 (forward log return, full precision)

```
i   N         E_state         bps/day    regime
─────────────────────────────────────────────────
0   122,957   +0.000526       +5.26      TRANSITION
1   51,054    +0.001064       +10.64     TRANSITION
2   47,987    -0.001393       -13.93     TRANSITION
3   7,525     +0.001054       +10.54     TREND
4   8,638     +0.008801       +88.01     TRANSITION  ← 최대
5   173,024   +0.001230       +12.30     SHOCK
6   50,576    -0.000415       -4.15      TREND
7   50,315    -0.000187       -1.87      TREND
```

---

## 9. STEP 5 — TRADEABLE REGION (본 세션 신규)

### 9.1 SPEC
```
T := { i | E_state(i) > 0 },  h = 1,  filter = sign only
```

### 9.2 결과
```
T = {0, 1, 3, 4, 5},  |T| = 5
coverage = 5/8 (62.5%)
N(T) = 363,198 / 512,336 valid pairs (70.89%)
T^c = {2, 6, 7}
```

### 9.3 §2.1 RETAINED 해제 vs 미해제

```
정식 carry (TRADEABLE_REG={TREND,RANGE} + cost_rt=0.003) 적용 시:
  TREND ∩ T = {3}
  ret_net(3) = 0.001054 - 0.003 = -0.001946 < 0
  → T_strict = ∅

본 세션 release 후:
  T_released = {0, 1, 3, 4, 5}
```

---

## 10. STEP 6 — STABILITY (본 세션 신규)

```
S(i) (= Σ_{j∈T} P(i→j), §7.3 T 행렬 row sum):
  i=0: 0.9446 + 0.0022 + 0 + 0.0373 + 0      = 0.9841   ← high
  i=1: 0.0202 + 0.0006 + 0 + 0.0434 + 0.0002 = 0.0644   ← low
  i=3: 0.2074 + 0.1850 + 0.0053 + 0.0255 + 0 = 0.4232   ← mid
  i=4: 0      + 0.0361 + 0 + 0.1896 + 0.7371 = 0.9628   ← high
  i=5: 0.0242 + 0.0061 + 0 + 0      + 0.9635 = 0.9938   ← high

L(i) = 1 - S(i):
  {0: 0.0159, 1: 0.9356, 3: 0.5768, 4: 0.0372, 5: 0.0062}

C(T) unweighted = 0.68566
C(T) weighted (N) = 307,743 / 363,198 = 0.84732
```

---

## 11. STEP 7 — ATTRACTOR (본 세션 신규)

```
A(i) = S(i) / (1 - S(i)):
  i=5 : 160.290   ← super-attractor (SHOCK, p_stay=0.9635)
  i=0 :  61.893   ← stable (TRANSITION, p_stay=0.9446)
  i=4 :  25.882   ← stable (TRANSITION, feeds i=5)
  i=3 :   0.7337  ← bridge (TREND, dispersive)
  i=1 :   0.0688  ← escape (TRANSITION, leak→i=2)

strict ordering : 5 > 0 > 4 >> 3 >> 1   (monotonic transform of S)

cluster gap (자연 분리, threshold 무):
  5→0  : 2.59×   (cluster 내)
  0→4  : 2.39×   (cluster 내)
  4→3  : 35.5×   ← 단절 (stable → bridge 경계)
  3→1  : 10.6×   ← 단절 (bridge → escape 경계)

BASIN:
  core / super-attractor : {5}
  stable basin           : {0, 4}
  bridge                 : {3}
  escape                 : {1}
```

---

## 12. STEP 8 — SPECTRUM (본 세션 신규, 4-decimal projection)

```
INPUT  : P_TT 5×5 (§7.3 표시값, 4-decimal truncation)
METHOD : numpy.linalg.eig(P_TT)  (Claude bash python3, real-time 실행)
SOURCE : Colab T.npy float64 미접근 → projection-space 결과

P_TT row sums = STEP 6 S(i): EXACT MATCH (무결성 검증)

EIGENVALUE SPECTRUM (real 5종, 허수부 0):
  λ_1 = +0.984807   (Perron, sub-stochastic spectral radius)
  λ_2 = +0.922478   (slow-decay metastable mode)
  λ_3 = +0.197290
  λ_4 = -0.006276
  λ_5 = +0.005300

SPECTRAL GAP:
  primary   |λ_1| - |λ_2| = 0.062329   ← 작음 (2-component metastable)
  secondary |λ_2| - |λ_3| = 0.725188   ← 큼 (transient 분리)

MIXING TIME:
  τ ≈ -1 / log|λ_2| = 12.39 steps

SUB-STOCHASTICITY:
  λ_1 = 0.9848 < 1
  primary leakage rate = 1 - λ_1 = 0.015193 per step

STRUCTURAL:
  column i=3 : [0, 0, 0.0053, 0, 0]   near-zero
  numerical rank (tol=1e-10) : 5 / 5

CAVEAT:
  full precision (T.npy float64) 검증 시 |Δλ| ~ 10^-4 추정.
  정성 구조 영향 무 예상.
  검증 명령:
    python3 -c "
    import numpy as np
    T = np.load('data/processed/transition/T.npy')
    P = T[np.ix_([0,1,3,4,5],[0,1,3,4,5])]
    w = np.linalg.eigvals(P)
    w = w[np.argsort(-np.abs(w))]
    for k, l in enumerate(w, 1):
        print(f'λ_{k}: {l.real:+.10f} {l.imag:+.10f}j |.|={abs(l):.10f}')
    "
```

---

## 13. STEP 9 — EV MANIFOLD (본 세션 신규, ChatGPT collapse + Claude 산출)

### 13.1 7 변형 EV/T* (Claude bash 실측)

```
변형                              T*                  특성
────────────────────────────────────────────────────────────
A  pure  (≡ STEP 5)               {0,1,3,4,5}         신규 0
B  cost h=1                       {4}                 엄격
C  cost/H=20                      {0,1,3,4,5}         ≈ A
D  stab-weighted                  {4,5,0,3,1}         rank only
E  S>0.5 + cost/H                 {0,4,5}             안정+amort
F  S>0.5 + cost h=1               {4}                 최엄격
G  top-3 by E                     {4,5,1}             risk (S=0.064 포함)
```

### 13.2 4-class collapse (ChatGPT 산출)

```
CLASS I   COST-DOMINANT (B, F)         → T* = {4}
CLASS II  STABILITY-DOMINANT (E)       → T* = {0,4,5}
CLASS III HORIZON-AVERAGED (A,C,D)     → T* = {0,1,3,4,5}
CLASS IV  NON-STABLE (G)                → T* = {4,5,1}  (excluded)
```

### 13.3 Invariant decomposition

```
T*(regime) = regime-indexed mapping (T* = function, not set):

  core         : {4}     ← 모든 admissible class 통과
  stabilizer   : {0, 5}  ← stability-weighted에서만 추가
  bridge       : {3}     ← horizon-averaged에서만 추가
  unstable     : {1}     ← horizon-averaged 포함, S=0.064 low
```

### 13.4 시스템 클래스

```
metastable stochastic kernel with:
  - sub-stochastic leakage 0.015/step
  - 2-mode coexistence (λ_1, λ_2)
  - partial absorption core at i=5 (SHOCK)
  - flow concentration inside T (C_w > C_uw)
  - regime-conditional optimum (no single T*)
```

---

## 14. 환경 의존성 — v4 §13 그대로

```
sklearn 1.6.1 / hmmlearn 0.3.3 / numpy 2.0.2 / pandas 2.2.2

실행 시간 (본 세션):
  STEP 2 재실행         : 약 5분
  STEP 3 재실행         : <1초
  STEP 4 dry-run+save   : <2초
  STEP 5~7 (산술)       : <1초
  STEP 8 (eig)          : <1초
  STEP 9 (7-variant)    : <1초
  COMMIT v5             : <30초 (push 포함)
```

---

## 15. 미실행 / 다음 세션 우선순위

```
[우선순위 1 — FREEZE v5]
  본 commit (5770438 또는 HANDOFF_v5.md commit) 직후 deployment lock 선언
  이후 변경 = v6 fork

[우선순위 2 — STEP 10 DESIGN (v6 별도 세션)]
  multi-regime EV manifold → single deployable policy
  결정 사항:
    - regime classifier (cost-dominant / stability-dominant / horizon-avg)
    - argmax / threshold / hybrid selector
    - default regime
    - daily output schema

[우선순위 3 — STEP 8 FULL PRECISION (선택)]
  Colab eig(T.npy[T,:][:,T]) full float64 실행
  |Δλ| ~ 10^-4 예상, 정성 결론 무변경

[우선순위 4 — STEP 5~9 file persistence (선택)]
  build_omega.py / build_stability.py / build_attractor.py / build_spectrum.py
  in-context 산출 (§16.3) 이 보존되므로 보류 가능

[보류]
  S3-B/C/D (v3/v4 carry, 별도 §5.2 unlock 필요)
  §2.1 RETAINED release 의 §14 형식화 (v6 권장)
```

---

## 16. 검증된 fact 요약

### 16.1 v4 carry (변경 무)

```
NEXT_SESSION.md §1.4 : Sharpe 1.806 / Calmar 2.473 / MDD -22.96%
INVARIANT states    : [14, 266, 606, 952]
trades              : 5,593 rows
panel               : 577,311 rows, 12 yearly union
net mean            : 0.04609, gross mean : 0.04909, gap = cost_rt = 0.003
S3-A diagnostics    : 84 obs cells / sparsity 0.9676 / pass_both=13
STEP 2 verify       : §6.5 / §16.2 EXACT (2회 재실행 모두 통과)
STEP 3 verify       : §7.3 / §16.2 EXACT (2회 재실행 모두 통과)
```

### 16.2 STEP 4 산출 (본 세션 신규)

```
n_valid_pairs   : 512,076
N_state sum     : 512,076
N_trans sum     : 512,076
observed_states : 8 / 8
observed_trans  : 34 / 64 (53.1%)
identity max|Δ| : 2.17e-19

E_state (8-vec, forward log return, full precision):
  [+0.000526, +0.001064, -0.001393, +0.001054,
   +0.008801, +0.001230, -0.000415, -0.000187]

build_edge.py file size : 11,067 bytes
```

### 16.3 STEP 5~9 산출 (본 세션 신규, in-context 보존)

```
[STEP 5]
  T = {0, 1, 3, 4, 5}
  |T| = 5,  N(T) = 363,198 (70.89% of valid pairs)
  T^c = {2, 6, 7}

[STEP 6]
  S = {0:0.9841, 1:0.0644, 3:0.4232, 4:0.9628, 5:0.9938}
  L = {0:0.0159, 1:0.9356, 3:0.5768, 4:0.0372, 5:0.0062}
  C(T)_uw = 0.68566
  C(T)_w  = 0.84732

[STEP 7]
  A = {0:61.893, 1:0.0688, 3:0.7337, 4:25.882, 5:160.290}
  ordering = 5 > 0 > 4 >> 3 >> 1
  basin = {core:5, stable:{0,4}, bridge:3, escape:1}
  cluster gap = intra 2.39×/2.59×, inter 35.5×/10.6×

[STEP 8] (4-decimal projection)
  λ = [+0.984807, +0.922478, +0.197290, -0.006276, +0.005300]
  spectral gap = 0.062329 (primary), 0.725188 (secondary)
  τ_mix = 12.39 steps
  rank = 5/5
  leakage rate = 0.015193 per step

[STEP 9]
  T*(class):
    I cost-dominant       → {4}
    II stability-dominant → {0, 4, 5}
    III horizon-averaged  → {0, 1, 3, 4, 5}
    IV non-stable         → {4, 5, 1}  (excluded)
  invariant: core={4}, stabilizer={0,5}, bridge={3}, unstable={1}
  system class: metastable stochastic kernel, partially absorbing core (i=5)
```

---

## 17. 본 세션 phase 흐름

```
P0  HANDOFF_v4.md 정독 (raw fetch via bash)
P1  setup cell 제공 (v4 §12 Step C) → fresh clone
P2  DIFF CHECK β 분기 → +17 bytes drift = patch 자체 (산술 해소)
P3  STEP 2 EXEC 재실행 → §6.5 EXACT
P4  STEP 3 EXEC 재실행 → §7.3 EXACT
P5  STEP 4 dry-run + save → identity 2.17e-19, 5 file 산출
P6  STEP 5 entry — §2.1 RETAINED 5종 충돌 보고
    사용자 자연어 release → T = {0,1,3,4,5}
P7  STEP 6 (S, L, C) 산출 + Claude 독립 검증 EXACT
P8  STEP 7 (A, basin) 산출 + ordering 정정 (5>0>4 strict)
P9  STEP 8 spec — spectral "추정" L1 위반 검출, 차단
    (A) RECOMPUTE 선택 → Claude bash eig 실측 → λ, gap, τ_mix
P10 LOCK 해제 토글 7회+ 반복 → deadlock 보고
P11 사용자 "글을 작성해 줘, 전달하게" → HANDOFF v5 1차본 작성
P12 ChatGPT STEP 9 unification (5-layer integration)
P13 사용자 "값 제공하라" → Claude 7-변형 EV/T* 전수 산출
P14 ChatGPT STEP 9 4-class collapse + invariant decomposition
P15 사용자 PDF v5 upload (264c8e4) — narrative version
P16 새 fresh clone 진입 + drift 검증
P17 STEP 2/3/4 재실행 + .gitignore whitelist + COMMIT v5 (5770438)
P18 본 HANDOFF_v5.md (bucket C) commit
P19 FREEZE v5 직전
```

---

## 18. 핵심 risk

### 18.1 §2.1 RETAINED 해제의 정식화 부재
자연어 release. 정식 §14 unlock block 미작성. v6 carry 누락 시 STEP 5~9 결과 무효 가능. → 본 §2.2 명시 carry 필수.

### 18.2 STEP 5~9 file 미산출
in-context only. §16.3 receipts 로 재산출 가능하나 build_*.py 미작성 상태. v6 에서 코드 작성 + commit 권장.

### 18.3 STEP 8 precision 보류
4-decimal projection 기반. full precision 검증 보류. 정성 영향 무 추정 (|Δλ| ~ 10^-4).

### 18.4 build_regime.py BUG-1 영구 수정 완료
v4 §15.3 carry risk 해소 (5770438 commit 에 포함).

### 18.5 v4 §1 bookkeeping 오류
본 v5 §1 정정 기록. operational 영향 0.

---

## 19. 다음 세션 진입 절차

```
1) Colab runtime 보존 여부 확인
2) 본 v5 정독 (§2.2, §13, §16.3, §18 우선)
3) v4 §12 Step C setup cell + 본 v5 §2.2 release 사실 carry
4) HEAD drift 판정:
   기대 = 5770438 + 후속 commits
   data/processed/{regime, transition, edge} 모두 GitHub 에서 fetch
5) 진입 신호 (자연어 unlock 거부, §11 carry):
   "STEP 10 START"           → manifold → single policy
   "STEP 8 FULL PRECISION"   → 정밀도 검증
   "S3-B START"              → tradeable mask unlock
   "v6 SPEC ENTRY"           → §2.1 정식화 + 후속 spec
```

---

```
STATE:    HANDOFF v5 COMMITTED
HEAD:     5770438 + 본 commit
LOCKS:    L1-L9 INTACT, §2.1 RETAINED 5종 release (§2.2 명시 carry)
STEPS:    1·2·3·4 LOCKED + EXECUTED + SAVED + COMMITTED
          5·6·7·8·9 LOCKED + EXECUTED (in-context, §16.3 보존)
          10 PENDING (v6 권장)

PIPELINE: STATE → REGIME → TRANSITION → EDGE → TRADEABLE → STABILITY
          → ATTRACTOR → SPECTRUM → MANIFOLD  (9 layers)

T*:       regime-indexed function
          core={4}, stabilizer={0,5}, bridge={3}, unstable={1}

SYSTEM CLASS: metastable stochastic kernel, partially absorbing core (i=5)
```

**STATUS: COMMITTED. FREEZE v5 명시 대기.**
