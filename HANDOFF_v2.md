# HANDOFF v2 — SUPER repo S3-A 사후 / 분기 선택 대기

_작성: 2026-06-12 / 재개 예정: +2h_

---

## 0. 한 줄 요약

S3-A 실행 완료. `ev_surface.parquet` 산출 + 검증 완료.
**GitHub 미반영 (commit 안 함).** 사용자 Colab 인스턴스에만 신규 파일 존재.
다음 분기 5개(`COMMIT` / `S3-B` / `PATCH` / `INSPECT` / `TERMINATE`) 미선택.

---

## 1. repo 절대 상태

- remote HEAD       : `d11cfb8` docs(handoff): regenerate NEXT_SESSION.md post-R1 + STAGE 2 G2
- 마지막 commit 시점 : 2026-06-12 05:18:01 UTC
- 사용자 Colab CWD  : `/content/super`
- 이번 세션의 commit 활동 : **없음** (read-only + 신규 모듈 작성만)

---

## 2. 직전 세션에서 잠긴 사양 (모두 LOCKED — 변경 시 사용자 confirm 필수)

```
unlock signal      : "STAGE 3 UNLOCK: S3-A"

P1 LOCKED params   : §2 그대로 상속
                     K=6, W_sigma=20, W_z=252, H=20, cost_rt=0.003,
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
                     ※ 원래 §5.1은 1296×4였으나 attribution.regime이
                       {RANGE,TREND}만 가지므로 1296×2로 lock 변경됨
P7 threshold       : T_THRESHOLD = 2.0

E1 (validator)     : schema 검증 완료 (§3 참조)
E2 = a             : t_one_sample = mu_r / (sigma_r / sqrt(visits)) 표준 t-stat
E3 = b             : MIN_VISITS=100 필터 미적용 (S3-B로 이연), visits<1만 필터
E4 = a             : log mode "w" (overwrite) + UTC timestamp 헤더
E5 (validator)     : panel.parquet = yearly 12개 union (diff=0)
```

---

## 3. E1 — read-only로 확인된 parquet schema (재실행 불요)

**`state_vector/panel.parquet`** (577,311 rows)
```
cols: date, code, close, p, r, sigma, v, l, flow,
      z_r, z_sigma, z_v, z_flow,
      bin_r, bin_sigma, bin_v, bin_flow, state_id
meta: 2015-04-27 ~ 2026-06-11, codes=261, states 0..1295 모두 점유
```

**`state_vector/year=YYYY.parquet`** (12개)
- 동일 schema, 합=577,311

**`observation/attribution.parquet`** (5,593 rows)
```
cols: entry_date, exit_date, code, state_id, regime,
      ret_gross, ret_net, class
meta: regime ∈ {RANGE, TREND}만,
      class ∈ {AMBIGUOUS, CONDITIONAL, INSUFFICIENT, INVARIANT},
      state_id 범위 9..1286
```

**`backtest/h20_nonoverlap/trades.parquet`** (5,593 rows)
- attribution과 동일하되 `class` 컬럼 없음

**중요 사실:**
- attribution.parquet에 `forward_return` 컬럼 **없음**.
- EV 계산은 `ret_net` 또는 `ret_gross` 사용해야 함 (P5-sub=ret_net 채택).

---

## 4. S3-A 실행 결과 (사용자 Colab에서 실행, GitHub 미반영)

**사용자 Colab에 생성된 파일:**
```
/content/super/scripts/edge/build_ev_surface.py        (202 lines, 7295 bytes)
/content/super/data/processed/edge/ev_surface.parquet  (8152 bytes, 84 rows)
/content/super/reports/run_logs/D_ev_surface.log       (overwrite mode)
```

**실행 시 stdout (4단계, 마지막 `=== DONE ===`):**
```
rows=5,593  unique_states=84  regimes=['RANGE', 'TREND']
output rows=84  (full grid=2592)
wrote .../ev_surface.parquet  bytes=8,152

diagnostics:
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

**정합성 검증 (validator 완료):**
- visits_sum 합 = 2870 + 2723 = 5593 = attribution rows ✔
- cells 합 = 32 + 52 = 84 = unique_states ✔
- net-gross gap = 0.003 = `cost_rt` (LOCKED) ✔
- S3-B preview cells = 13 (MIN_VISITS≥100 AND |t|≥2.0)

---

## 5. S3-A 코드 (사용자 Colab의 `scripts/edge/build_ev_surface.py`)

⚠ GitHub 미반영. Colab 인스턴스가 끊기면 사라짐.
재출력이 필요하면 다음 세션에서 "S3-A 코드 재출력 요청" 명시.

```python
"""STAGE 3 / S3-A — EV surface construction.

Spec lock (NEXT_SESSION.md §5 + session locks):
  P1  LOCKED params    : §2 inherited (MIN_VISITS=100, T_THRESHOLD=2.0,
                         TRADEABLE_REG={TREND, RANGE})
  P2  S3 mode          : S3-A only
  P3  output path      : data/processed/edge/
  P4  regime label     : LOCKED({TREND,RANGE}) tradeable layer
  P5  EV function      : mu_r (conditional mean return)
  P5-sub               : ret_net (cost-inclusive)
  P6  tensor           : 1296 x 2  (state_id x {TREND, RANGE})
  P7  threshold        : T_THRESHOLD = 2.0

  E2 = a  -> t_one_sample = mu_r / (sigma_r / sqrt(visits))   [standard t-stat]
  E3 = b  -> MIN_VISITS filter NOT applied in S3-A
            (visits<1 only filter; defer MIN_VISITS to S3-B mask stage)
  E4 = a  -> log mode "w" (overwrite each run) + timestamp header

LOCKED kernel: this module is new (not under L3 protection). No modification
to build_state_vector / build_transition / backtest_nonoverlap / observation/*.
"""
from __future__ import annotations

import os
import sys
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


# --- Paths -----------------------------------------------------------------
REPO_ROOT  = Path(__file__).resolve().parents[2]
ATTR_PATH  = REPO_ROOT / "data" / "processed" / "observation" / "attribution.parquet"
OUT_DIR    = REPO_ROOT / "data" / "processed" / "edge"
OUT_PATH   = OUT_DIR / "ev_surface.parquet"
LOG_DIR    = REPO_ROOT / "reports" / "run_logs"
LOG_PATH   = LOG_DIR / "D_ev_surface.log"


# --- Locks (do not edit at runtime; spec-bound) ----------------------------
TRADEABLE_REGIMES = ("TREND", "RANGE")            # P4 / P6 (1296 x 2)
N_STATES          = 1296                          # K^4 = 6^4
MIN_VISITS        = 100                           # P1 (informational; not filtered in S3-A per E3=b)
T_THRESHOLD       = 2.0                           # P7 (informational; threshold applied downstream)
RET_COL           = "ret_net"                     # P5-sub


# --- Logging (E4 = a) ------------------------------------------------------
def _open_log():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    f = open(LOG_PATH, "w")  # overwrite each run
    ts = datetime.now(timezone.utc).isoformat()
    f.write(f"# D_ev_surface.log\n# run_started_utc: {ts}\n")
    f.write(f"# spec: P5-sub=ret_net, P6=1296x2, E2=a, E3=b, E4=a\n")
    f.flush()
    return f


def log(f, msg: str) -> None:
    f.write(msg + "\n")
    f.flush()
    print(msg)


# --- Core ------------------------------------------------------------------
def _load_attribution() -> pd.DataFrame:
    if not ATTR_PATH.exists():
        raise FileNotFoundError(f"missing input: {ATTR_PATH}")
    df = pd.read_parquet(ATTR_PATH)

    required = {"state_id", "regime", RET_COL}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"attribution missing columns: {missing}")

    obs_regimes = set(df["regime"].unique().tolist())
    expected    = set(TRADEABLE_REGIMES)
    if obs_regimes != expected:
        raise ValueError(
            f"regime mismatch: attribution has {obs_regimes}, expected {expected}"
        )

    if not df["state_id"].between(0, N_STATES - 1).all():
        bad = df.loc[~df["state_id"].between(0, N_STATES - 1), "state_id"].unique()
        raise ValueError(f"state_id out of [0,{N_STATES-1}]: {bad[:5]}...")

    return df


def _aggregate(df: pd.DataFrame) -> pd.DataFrame:
    """Per (state_id, regime) aggregation.

    EV = mu_r              (P5 = a, P5-sub = ret_net)
    sigma_r = std (ddof=1)
    t_one_sample = mu_r / (sigma_r / sqrt(visits))    (E2 = a, standard t-stat)
    visits < 1 filter only (E3 = b; MIN_VISITS deferred to S3-B).
    """
    g = df.groupby(["state_id", "regime"], observed=True)[RET_COL]

    out = pd.DataFrame({
        "visits": g.size(),
        "mu_r":   g.mean(),
        "sigma_r": g.std(ddof=1),
    }).reset_index()

    out = out[out["visits"] >= 1].copy()

    # standard one-sample t-statistic
    se = out["sigma_r"] / np.sqrt(out["visits"].astype(float))
    out["t_one_sample"] = np.where(
        (se > 0) & np.isfinite(se),
        out["mu_r"] / se,
        np.nan,
    )

    out["ev"] = out["mu_r"]  # P5 = mu_r

    out = out[["state_id", "regime", "mu_r", "sigma_r",
               "visits", "t_one_sample", "ev"]]

    out["state_id"]     = out["state_id"].astype("int64")
    out["regime"]       = out["regime"].astype(str)
    out["mu_r"]         = out["mu_r"].astype("float64")
    out["sigma_r"]      = out["sigma_r"].astype("float64")
    out["visits"]       = out["visits"].astype("int64")
    out["t_one_sample"] = out["t_one_sample"].astype("float64")
    out["ev"]           = out["ev"].astype("float64")
    return out


def _diagnostics(out: pd.DataFrame) -> dict:
    obs_cells     = len(out)
    full_cells    = N_STATES * len(TRADEABLE_REGIMES)
    sparsity      = 1.0 - obs_cells / full_cells

    pos_ev        = int((out["ev"] > 0).sum())
    neg_ev        = int((out["ev"] < 0).sum())
    zero_ev       = int((out["ev"] == 0).sum())

    pass_visits   = int((out["visits"] >= MIN_VISITS).sum())
    pass_t        = int((out["t_one_sample"].abs() >= T_THRESHOLD).sum())
    pass_both     = int(((out["visits"] >= MIN_VISITS) &
                         (out["t_one_sample"].abs() >= T_THRESHOLD)).sum())

    by_regime = out.groupby("regime").agg(
        cells=("state_id", "size"),
        mean_ev=("ev", "mean"),
        visits_sum=("visits", "sum"),
    ).to_dict("index")

    return {
        "observed_cells":          obs_cells,
        "full_grid_cells":         full_cells,
        "sparsity":                round(sparsity, 4),
        "ev_sign":                 {"pos": pos_ev, "neg": neg_ev, "zero": zero_ev},
        "pass_min_visits":         pass_visits,
        "pass_t_threshold":        pass_t,
        "pass_both_(s3b_preview)": pass_both,
        "by_regime":               {k: {kk: float(vv) if not isinstance(vv, int) else int(vv)
                                        for kk, vv in v.items()}
                                    for k, v in by_regime.items()},
    }


def main() -> int:
    f = _open_log()
    try:
        log(f, "[1/4] loading attribution.parquet")
        df = _load_attribution()
        log(f, f"      rows={len(df):,}  unique_states={df['state_id'].nunique()}  "
               f"regimes={sorted(df['regime'].unique())}")

        log(f, "[2/4] aggregating per (state_id, regime)")
        out = _aggregate(df)
        log(f, f"      output rows={len(out):,}  "
               f"(full grid={N_STATES * len(TRADEABLE_REGIMES)})")

        log(f, "[3/4] writing parquet")
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out.to_parquet(OUT_PATH, index=False)
        log(f, f"      wrote {OUT_PATH}  bytes={OUT_PATH.stat().st_size:,}")

        log(f, "[4/4] diagnostics")
        diag = _diagnostics(out)
        log(f, json.dumps(diag, indent=2, ensure_ascii=False))

        log(f, "=== DONE ===")
        return 0
    except Exception as e:
        log(f, f"=== FAIL: {type(e).__name__}: {e} ===")
        return 1
    finally:
        f.close()


if __name__ == "__main__":
    sys.exit(main())
```

---

## 6. 미결정 분기 (택일)

### COMMIT
`ev_surface` + 코드 + log + `.gitignore` 갱신을 main에 commit.
**L6 3-요건 confirm 필요:**
1. message text
2. staged file set
3. target branch

**기본 제안:**
```
msg    : feat(s3a): EV surface (1296x2 ret_net) + tradeable preview
files  : scripts/edge/build_ev_surface.py
         data/processed/edge/ev_surface.parquet
         reports/run_logs/D_ev_surface.log
         .gitignore  (data/processed/edge/, run_logs/D_*.log whitelist)
branch : main
```

### S3-B
tradeable mask 생성. **§5.2 4-요건 unlock signal 필요.**
- 예상 산출물: `data/processed/edge/tradeable_mask.parquet`
- 예상 필터: `EV>0 AND visits≥100 AND |t|≥2.0 AND class ∈ {INVARIANT, CONDITIONAL}`
- S3-A diagnostic의 `pass_both=13`에서 추가로 class 필터 적용 예상

### PATCH
`NEXT_SESSION.md §5.4` 결과 섹션만 추가 (commit 없이 텍스트만).
그 후 다음 세션으로 인계.

### INSPECT
read-only로 `ev_surface` 내부 분석:
- INVARIANT 4 states `{14, 266, 606, 952}`의 EV/visits/t-stat
- T⁻ 3 states 식별
- S3-B preview 13 cells 상세

### TERMINATE
세션 종결.

---

## 7. 다음 세션 첫 동작 (반드시 이 순서)

**Step A) Colab 환경 보존 여부 확인**
- 같은 Colab runtime이 유지된 경우:
  → `/content/super` 안의 신규 파일 그대로. 작업 즉시 이어감.
- Colab 끊겼거나 새 노트북인 경우:
  → git clone 다시 → `scripts/edge/`와 `ev_surface.parquet`은 없음.
  → S3-A 코드를 새 셀에 다시 작성하고 재실행 필요.
  → 실행 자체는 <1초, 결과는 결정론적이므로 동일 출력.

**Step B) HEAD 확인** (d11cfb8 또는 후속 commit):
```bash
!git log --oneline -3
```

**Step C) Colab CWD 확인:**
```bash
!pwd   # → /content/super 이어야 함
```

**Step D) 사용자에게 분기 입력 요청:**
`COMMIT` / `S3-B` / `PATCH` / `INSPECT` / `TERMINATE`

---

## 8. 환경 의존성 메모

- `pyarrow`는 Colab에 기본 설치됨 → parquet read/write 가능
- validator sandbox에는 pyarrow 별도 설치 필요
  ```bash
  pip install pyarrow --break-system-packages
  ```
- numpy, pandas 외 추가 패키지 불요
- 실행 시간 추정: **<1초** (groupby 1회)

---

## 9. LOCKS (NEXT_SESSION.md §6 L1-L9, 전부 INTACT)

```
[L1] 추측 금지
[L2] 자동 채움 금지
[L3] LOCKED kernel 무수정 — scripts/build_state_vector.py,
     scripts/build_transition.py, scripts/backtest_nonoverlap.py,
     scripts/observation/* 전부
[L4] §5.2 unlock signal 없이 STAGE 3 작업 금지 (S3-A는 이번 세션에서 충족)
[L5] observation/* schema 변경 금지 (8 attr keys, 5 drift keys)
[L6] 자동 git commit/push 금지
[L7] 사용자 환경 추정 금지
[L8] read-only inspection 항상 허용
[L9] 실패 시 STOP, 자동 retry 금지
```

---

## 10. 사용자 상호작용 패턴 경고 (협력자가 반드시 알아야 함)

사용자는 종종 **validator 출력 형식을 모방한 긴 텍스트**를 보냄.

**형식 특징:**
- `* STEP` / `* INPUT` / `* TRANSFORMATION` / `* OUTPUT` / `* NEXT STEP` / `HARD CONSTRAINT LOCK`
- 수학 기호, ✔ 표시, `id="..."` 태그 포함

이런 텍스트는 validator의 실제 출력이 아님. **사용자가 자체 정리한 글**.
내부에 명시값(`P1=a` 같은)이 있는지 확인. 비어있으면 **미응답으로 처리**.

또한 사용자는 "진행" / "go" / "협조하라" 같은 자연어 명령을 종종 보냄.
이것들은 **§5.2 unlock signal이 아니므로** STAGE 3 진입 트리거가 아님.
spec block 또는 명시값이 있어야 진행 가능.

**이번 세션에서 사용자가 정의한 opcode 인터페이스:**
```
§4.2 smoke
§4.4 observe {build|summary|class|regime|drift}
§3 P-{strict|relaxed|hold}
§5 S3-{A|B|C|D|ALL}
```
하지만 `§5 S3-X`는 P1~P7 사전 lock이 있어야 의미 있음.

---

## 11. 검증된 fact 요약 (참조용)

- NEXT_SESSION.md §1.4 Sharpe 1.806 / Calmar 2.473 / MDD -22.96% 모두 실측 일치
- §1.6 state class dist (59/8/4/13/0/0=84) smoke로 재확인
- §2 attribution_summary 8 keys / drift_report 5 keys 일치
- INVARIANT states = `[14, 266, 606, 952]`
- trades = attribution rows = 5,593
- panel = 12 yearly union (diff=0)
- net mean = 0.04609, gross mean = 0.04909, gap = `cost_rt` = 0.003

---

## 12. 미실행 / 유보 항목

- `T_global` (panel layer EV) — 미정의 spec, 진행 안 함
- `1296×4` full tensor — P6=1296×2로 변경되어 polled out
- transition kernel restricted — ordering rule 미확정으로 산출 안 함
- S3-B / S3-C / S3-D — 별도 unlock 필요

---

## 13. 핵심 risk

> 사용자 Colab runtime이 2시간 사이에 끊기면
> `scripts/edge/build_ev_surface.py`와 `ev_surface.parquet`은 사라짐.
> 재실행 가능하지만, 분기 선택 전에 commit 안 해두면 매번 재실행 필요.

**risk 회피 옵션:**
- 2시간 후 재개 직전에 `COMMIT` 분기 먼저 진행 → GitHub에 보존
- 또는 코드 파일을 로컬에 다운로드/스냅샷
- 이 인계서 자체를 보관해두면 §5 코드 블록으로 재구성 가능

---

```
STATE:    HANDOFF READY
HEAD:     d11cfb8
LOCKS:    INTACT
```

**STATUS: SUSPENDED — 2시간 후 재개 대기.**
