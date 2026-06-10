# SUPER — Market Structure Model (MSM) 세션 인계서

**작성일**: 2026-06-11
**프로젝트**: `stanleyim/super`
**환경**: Google Colab (Python 3.12.13, RAM 13.6GB, 2 cores)
**현재 단계**: STEP 8.5 완료 → STEP 9 진입 직전 (옵션 결정 대기)

---

## 1. 프로젝트 개요

### 목표
주식시장 OHLCV 데이터를 이산 Markov state system으로 변환 → positive expected value 영역만 추출.

### 파이프라인
```
RAW → CLEAN → STATE VECTOR → NORMALIZE → DISCRETIZE
    → REGIME → TRANSITION → EDGE → TRADEABLE → BACKTEST → OOS
```

### 데이터
- KRX 일봉, 262 종목 (실제 유효 261개)
- 기간: 2014-03-18 ~ 2026-06-10
- z-score normalize 후 가용 기간: 2015-04-27 ~ 2026-06-10
- causal binning 후 가용 기간: **2016-05-04 ~ 2026-06-10**
- 총 행 수: 513,848 (causal 처리 후)

---

## 2. 사용자 원칙 (절대 준수)

```
1. 통계/수치 기반 시장 흐름 예측 애플리케이션 개발
2. 모든 지식 동원, 헌신적 노력
3. 최고 사양 답변, 3번 검증, 에러 없는 완벽한 결과
4. 행동 전 목적 부합 여부 확인
5. 모르는 사항 추측 금지, 상의 우선, 거짓말 금지,
   함부로 코드 손대지 말 것, 변경/수정 전 사용자 의향 확인
6. 답변은 간결, 명확하게
```

---

## 3. STEP별 완료 상태 (최종)

| STEP | 상태 | 핵심 결과 |
|---|---|---|
| 1. Data Cleaning | ✅ 완료 | clean_panel: 650,054행 |
| 2. State Vector | ✅ 완료 | (p, r, σ, v, l), 644,814행 |
| 3. Normalization | ✅ 완료 (수정됨) | **z_p도 rolling z-score 적용** |
| 4. Discretization | ✅ 완료 (causal+fast) | **sliding_window_view 벡터화** |
| 5. Regime | ✅ 완료 (수정됨) | **TREND 조건: `m >= hi_mu`만 적용 (ISSUE 1)** |
| 6. Transition Matrix | ✅ 완료 | P sparse (7742×7742), nnz=260,060 |
| 7. Edge Field | ✅ 완료 (수정됨) | **N_MIN=100으로 완화** |
| 8. Backtest | ✅ 완료 | GROSS Sharpe ann=1.98, NET=0.58 |
| 8.5. OOS | ✅ 완료 | TEST Sharpe ann gross=2.17, net=0.84 |
| 9. Deployment | ⏸️ **대기 중** | 옵션 선택 대기 |

---

## 4. 최종 검증 결과 (CASE 1: DEPLOYABLE BASELINE)

### 4.1 전체 성능 (full sample)
| 지표 | GROSS | NET |
|---|---|---|
| n_trades | 663 | 663 |
| mean (per bar) | +0.00353 | +0.00103 |
| Sharpe (annualized) | **+1.978** | **+0.576** |
| Hit ratio | 0.526 | 0.490 |
| Cum return | +937.0% | +97.7% |

### 4.2 OOS 검증 (TRAIN: 2016~2022 / TEST: 2023~2026.06)
| 지표 | TRAIN | TEST |
|---|---|---|
| n | 427 | 236 |
| mean_gross | 0.0032 | 0.0041 |
| mean_net | 0.0007 | 0.0016 |
| **Sharpe ann gross** | 1.87 | **+2.17** |
| **Sharpe ann net** | 0.42 | **+0.84** |
| Hit gross | 0.522 | 0.534 |

**Stability ratios:**
- mean_g_ratio = +1.26 (target [0.7, 1.3]) ✅
- sh_g_ratio = +1.16 ✅

### 4.3 검증 통과 항목 (사용자 정의 기준)
- ✅ test sh_g > 0.5: **+2.17**
- ✅ test sh_n ≥ 0: **+0.84**
- ✅ mean_g_ratio ∈ [0.7, 1.3]: **+1.26**
- ⚠️ 연도별 net 양수: 6/11 (55%)

### 4.4 TRADEABLE 6 states
| state_id | regime | visits | p_stay | E_base | E_adj1 | E_adj3 | z_p_bin |
|---|---|---|---|---|---|---|---|
| 31 | TREND | 111 | 0.108 | +0.190 | +0.100 | +0.101 | 0 |
| 539 | TREND | 119 | 0.059 | +0.189 | +0.073 | +0.069 | 0 |
| 6593 | TREND | 112 | 0.036 | +0.193 | +0.043 | +0.048 | 5 |
| **4487** | **TREND** | **100** | **0.040** | **-0.236** | **+0.043** | **+0.041** | **3** |
| 6665 | TREND | 121 | 0.074 | +0.194 | +0.034 | +0.038 | 5 |
| 494 | TREND | 100 | 0.030 | +0.259 | +0.035 | +0.036 | 0 |

**z_p_bin 분포**: {0: 3, 3: 1, 5: 2} — 저가 reversal + 고가 momentum 혼합

### 4.5 핵심 관찰
- **state 4487**: 유일한 부정 신호 (E_base 음수, TEST sh=-5.48) → **제거 후보**
- **net 마진**: cost 25bps가 gross edge의 71% 잠식 → cost sensitivity 검증 필요
- **연도별 손실**: 2016, 2017, 2020, 2024, 2026 (net 기준 5/11 손실)
- **TEST > TRAIN**: 모델이 최근 시기에 더 잘 작동 (regime shift 가능성)

---

## 5. 발견된 결정적 문제 & 해결 이력

### 5.1 **CRITICAL: STEP 4 look-ahead 버그 (발견 → 수정)**
- **문제**: `pd.qcut(g[col], q=K)` 가 전체 시계열 기반 quantile → **future leakage**
- **증상**: OOS test Sharpe = 4.26 (비현실적), mean_ratio = 3.37
- **해결**: `sliding_window_view` 기반 strict causal rolling rank binning
- **수정 후**: test Sharpe = 2.17 (현실적), mean_ratio = 1.26
- **교훈**: causal validation 없이 결과 인용 절대 금지

### 5.2 **CRITICAL: z_p distortion (발견 → 수정)**
- **문제**: `z_p = log(close)` raw → trend asset에서 한쪽 쏠림
- **증상**: z_p bin 분포 양 끝 54% 집중 (이상: 16.7%×6=균등)
- **해결**: STEP 3에서 z_p도 다른 feature와 동일하게 rolling z-score 적용
- **수정 후**: z_p bin 양 끝 45% (다른 feature와 유사 수준)

### 5.3 **TREND scarcity at N_MIN=200 (구조적)**
- **문제**: z_p 수정 후 visits≥200에서 TREND = 0
- **분석**: 진짜 신호가 본질적으로 sparse (look-ahead가 만들었던 풍부함은 환영)
- **해결**: N_MIN=100으로 완화 (regime/edge/state 정의 불변, filter만 완화)
- **결과**: TREND 6개 등장 → OOS 통과

### 5.4 TREND 조건 수정 (ISSUE 1)
- **이전**: `elif m >= hi_mu and s >= med_sig: TREND`
- **수정**: `elif m >= hi_mu: TREND`  (`s >= med_sig` 제거)
- **근거**: low-vol trend (macro drift) 포착

### 5.5 보류된 이슈 (ISSUE 2, 3)
- **ISSUE 2**: SHOCK/TRANSITION overlap → 보류 (baseline 우선)
- **ISSUE 3**: entropy scaling → 보류

---

## 6. 디렉토리 구조 & 캐시 파일

### 6.1 작업 디렉토리
```
/content/super/                  (cwd)
├── data/
│   ├── raw/ohlcv/
│   │   └── year=2014.parquet ~ year=2026.parquet (13개)
│   └── cache/
│       ├── clean_panel.parquet          (5.3MB)
│       ├── state_vector_raw.parquet     (21.2MB)
│       ├── state_vector_norm.parquet    (40.3MB, z_p 수정판)
│       └── state_disc.parquet           (37.7MB, causal+z_p수정)
└── model/
    ├── state_table.parquet              (regime, E_*, p_stay 포함)
    ├── transition_P.npz                 (sparse 7742×7742)
    ├── tradeable.parquet                (6 states)
    └── (oos_*.parquet 등)
```

### 6.2 Colab Secrets (환경변수)
```
GH_TOKEN     : OK
KRX_ID       : OK
KRX_PW       : OK (원본 KRK_PW 오타로 추정, KRX_PW 사용 중)
KRX_API_KEY  : OK
```

---

## 7. 핵심 파라미터 (확정)

```python
# STEP 3 — Normalization
WINDOW    = 252
EPS       = 1e-8
STD_FLOOR = 1e-6      # ← 변경됨 (이전 1e-4)
Z_CLIP    = 5.0       # ← 변경됨 (이전 10.0)
NORM_COLS = ["r", "sigma", "v", "l", "p"]   # ← p 추가

# STEP 4 — Discretization
K        = 6
BIN_COLS = ["z_r", "z_sigma", "z_v", "z_l", "z_p"]
WEIGHTS  = [1, 6, 36, 216, 1296]   # base-K positional

# STEP 5 — Regime
# Thresholds: σ Q70/Q30, |μ| Q70, entropy median (per-state stats 기반)
# 규칙:
#   SHOCK:      s >= hi_vol AND h >= med_ent
#   TREND:      m >= hi_mu                    # ← s 조건 제거 (ISSUE 1)
#   RANGE:      s <= lo_vol AND m < med_mu
#   TRANSITION: else

# STEP 7 — Edge Field
N_MIN = 100           # ← 변경됨 (이전 200)
Q     = 0.70          # rank_adj3 threshold

# STEP 8 — Backtest
COST_BPS    = 0.0025  # 25bps round-trip
ANNUAL_BARS = 252
HOLD        = 1       # 1-bar hold (p_stay 낮음 근거)
```

---

## 8. 다음 세션 빠른 재시작 가이드

### 8.1 환경 복구 셀 (Colab)

```python
# Cell 1: 환경 + secrets
import os, sys, subprocess, psutil
from google.colab import userdata

for k in ["GH_TOKEN", "KRX_ID", "KRX_PW", "KRX_API_KEY"]:
    try: os.environ[k] = userdata.get(k)
    except: pass

REPO_DIR = "/content/super"
if not os.path.exists(REPO_DIR):
    url = f"https://{os.environ['GH_TOKEN']}@github.com/stanleyim/super.git"
    subprocess.run(["git", "clone", url, REPO_DIR], check=True)
os.chdir(REPO_DIR)
print(f"cwd: {os.getcwd()}, Python: {sys.version.split()[0]}")
```

```python
# Cell 2: 모든 캐시 로드 (STEP 1~8.5 결과 복원)
import os, glob, psutil
import numpy as np
import pandas as pd
from scipy.sparse import load_npz

CACHE_DIR = "data/cache"
MODEL_DIR = "model"

def ram():
    m = psutil.virtual_memory()
    return f"RAM {m.percent:.1f}% (avail {m.available/1e9:.1f}GB)"

def load(name, dir_=CACHE_DIR):
    p = f"{dir_}/{name}.parquet"
    df = pd.read_parquet(p)
    if {"date","code"}.issubset(df.columns):
        df = df.set_index(["date","code"]).sort_index()
    return df

clean_panel       = load("clean_panel")
state_vector_raw  = load("state_vector_raw")
state_vector_norm = load("state_vector_norm")
state_disc        = load("state_disc")
state_table       = load("state_table", MODEL_DIR)
tradeable         = load("tradeable",   MODEL_DIR)

# transition matrix
P = load_npz(f"{MODEL_DIR}/transition_P.npz")

# sid_to_idx 재생성
all_states = state_table["state_id"].values
sid_to_idx = pd.Series(np.arange(len(all_states)), index=all_states)
regime_map = state_table.set_index("state_id")["regime"]

print(f"✅ 전체 캐시 복원 완료 | {ram()}")
print(f"   state_disc: {state_disc.shape}")
print(f"   state_table: {state_table.shape}")
print(f"   tradeable: {len(tradeable)} states")
print(f"   P: {P.shape}, nnz={P.nnz:,}")
```

### 8.2 검증 (재실행 후 동일 결과 확인)

```python
# tradeable이 6개, state_id가 [31, 494, 539, 4487, 6593, 6665] 이면 정상
expected = sorted([31, 494, 539, 4487, 6593, 6665])
actual = sorted(tradeable["state_id"].astype(int).tolist())
assert actual == expected, f"불일치: {actual} vs {expected}"
print("✅ 검증 통과: tradeable 상태 일치")
```

---

## 9. 미결 결정 사항 (NEXT)

### 9.1 STEP 9 진입 옵션 (사용자 선택 대기)

**옵션 A (권장): Robustness 추가 검증**
- state 4487 제거 후 재평가 (false positive 제거)
- Walk-forward 검증 (단순 split보다 강건)
- Drawdown / Maximum DD profile
- Cost sensitivity (15/25/35 bps)

**옵션 B: STEP 9 (Deployment Filter) 즉시 진행**
- `rank_adj3 > 0.85` 강화
- Position sizing (E_adj3 weighted)
- 실시간 signal generation 로직

**옵션 C: 다른 변형 실험 (Sensitivity)**
- N_MIN sweep (50, 100, 150, 200)
- Q sweep (0.6, 0.7, 0.8, 0.9)
- regime constraint sensitivity

### 9.2 추후 검토 사항 (deferred)

1. **state 4487 처리**
   - E_base = -0.236 (음수)인데 E_adj1 = +0.043 (양수)
   - transition operator의 false positive 의심
   - TEST에서 -5.48 Sharpe로 손실 발생
   - 제거 vs 보존 결정 필요

2. **ISSUE 2 (SHOCK/TRANSITION overlap)**: 보류 중
3. **ISSUE 3 (entropy scaling)**: 보류 중

4. **2014 데이터 손실**
   - state_vector_norm 시작: 2015-04-27 (252일 warmup)
   - state_disc 시작: 2016-05-04 (추가 252일 warmup)
   - 총 손실 기간: 약 2년
   - **불가피한 비용** (causal 유지 위해)

5. **z_p_bin 분포 잔존 distortion**
   - 양 끝 합 45% (목표 33% = 16.7×2)
   - 가격 시계열 본질적 특성으로 추정
   - 추가 개선 시 옵션 E (momentum): `z_p = log(close/close.shift(252))`

---

## 10. 핵심 코드 스니펫 (재사용)

### 10.1 STEP 4 — Causal Rolling Rank Binning (fast)

```python
from numpy.lib.stride_tricks import sliding_window_view

def rolling_rank_bin_fast(arr, window, K):
    """Strict causal: bin at t uses [t-window, t-1] only.
    sliding_window_view 벡터화로 ~60배 빠름."""
    n = len(arr)
    out = np.full(n, np.nan, dtype=np.float64)
    if n <= window: return out
    past = sliding_window_view(arr, window)[:-1]  # row i → arr[i:i+window]
    targets = arr[window:]                         # t = i + window
    cmp = past < targets[:, None]
    valid = ~np.isnan(targets) & ~np.isnan(past).any(axis=1)
    rank_pct = np.where(valid, cmp.sum(axis=1) / window, np.nan)
    bins = np.clip(np.floor(rank_pct * K), 0, K-1)
    out[window:] = bins
    return out
```

### 10.2 Regime Assignment (확정)

```python
def assign_regime(row):
    s, m, h = row["sigma_r"], abs(row["mu_r"]), row["entropy"]
    if s >= hi_vol and h >= med_ent: return "SHOCK"
    elif m >= hi_mu:                  return "TREND"    # ← ISSUE 1
    elif s <= lo_vol and m < med_mu:  return "RANGE"
    else:                             return "TRANSITION"
```

### 10.3 Edge Operators

```python
state_table["E_base"] = state_table["mu_r"]
state_table["E_adj1"] = state_table["E_trans"]
state_table["E_adj2"] = state_table["E_trans"] * state_table["p_stay"]
state_table["E_adj3"] = state_table["E_trans"] / np.sqrt(state_table["Var_full"] + EPS)
```

---

## 11. 주의사항 (다음 세션에서 반드시 인지)

### 11.1 절대 금지
- ❌ STEP 4 `pd.qcut` 사용 — look-ahead 발생, 결과 무효화됨
- ❌ Sharpe 0.5 기준 bar 단위로 판정 — 연율화 기준이어야 의미 있음
- ❌ tradeable 비어있을 때 regime 정의 변경 — 구조 오염
- ❌ 캐시 무효화 없이 STEP 변경 — stale data 사용 위험

### 11.2 반드시 준수
- ✅ 모든 normalization에 shift(1) 적용 (strict causal)
- ✅ Bin uniformity 16.7% ± 3% 범위 확인
- ✅ Net Sharpe 양수 확인 (deployable 조건)
- ✅ mean_ratio ∈ [0.7, 1.3] 확인 (OOS stability)
- ✅ 구조 변경 전 사용자 의향 확인 (userPreferences 5번 원칙)

### 11.3 검증 시그널 (CASE 분류표)
| CASE | 조건 | 다음 액션 |
|---|---|---|
| 1 (DEPLOYABLE) | mr ∈ [0.7,1.3], sh_g>0.5, sh_n≥0 | STEP 9 진입 |
| 1.5 (WEAK PASS) | sh_g>0, but stability 부족 | conservative deployment |
| 2 (FAIL) | sh_g≤0 OR mr<0.5 | STEP 3/4 재설계 |

---

## 12. 마지막 컨텍스트 (사용자 마지막 결정 시점)

**사용자 마지막 발언**: STEP 8.5 결과 확인 후 "세션 인계서 md file 로 상세히 작성" 요청

**Claude 마지막 제안 (대기 중)**:
> 옵션 1 (Robustness) → 옵션 2 (STEP 9) 순서 권장. 선택 주세요:
> - A. 옵션 1 (robustness, 권장)
> - B. 옵션 2 (STEP 9 직진)
> - C. 옵션 3 (sensitivity)
> - D. 다른 방향

**다음 세션 첫 액션**:
1. 위 환경 복구 셀 2개 실행 (10초)
2. 검증 셀 실행 (assert 통과 확인)
3. 사용자가 옵션 A/B/C/D 중 선택
4. 선택에 따라 진행

---

## 13. 참고 — Repo 정보

- **URL**: https://github.com/stanleyim/super/
- **README**: super/README.md
- **데이터 소스**: KRX OHLCV (자체 수집)
- **언어**: Python 3.12.13
- **주요 라이브러리**: pandas 2.2.2, numpy 2.0.2, scipy 1.16.3, pyarrow 18.1.0

---

**문서 끝.**
다음 세션 시작 시 이 파일을 그대로 첨부하면 컨텍스트 완전 복원 가능.
