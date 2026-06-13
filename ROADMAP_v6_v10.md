# SUPER repo — v6 → v10 FINAL ROADMAP

작성: 2026-06-13
기준: v5 FROZEN (tag v5.0, HEAD 338c71e)
반영: ChatGPT 정정 3건 + Claude 보완 2건 + ChatGPT patch 2건 + Claude pending 3건

---

## 0. SYSTEM ARCHITECTURE

```
v6    signal kernel (EV manifold execution)
v6.5  calibration GATE (binary PASS/FAIL)
v7    statistical robustness (walk-forward CV)
v8    risk regime extension (BRANCH POINT, long-only default)
v9    productionization (live system)
v10   monitoring / lifecycle
```

**3-layer hierarchy**:
- v6 ~ v7 : signal validity layer
- v8      : risk policy layer (branch point)
- v9      : execution layer
- v10     : system health layer

**Quality assessment** (ChatGPT 평가):
- v6 kernel       : SOLID
- v6.5 gate       : STRONG (deterministic binary)
- v7 validation   : STRONG (aggregation rule defined)
- v8 risk branch  : VERY GOOD (explicit override design)
- v9 production   : INDUSTRY LEVEL
- v10 monitoring  : ADVANCED (drift/regime separation)
- OVERALL         : 9.2 / 10 production-grade research system

---

## 1. v6 — Signal Kernel

### 1.1 SPEC LOCK (V6_ENTRY.md §2)

```
T_star      = CLASS III = {0, 1, 3, 4, 5}
action set  = {0, +1}                    (long-only)
allocation  = equal weight cross-sectional
horizon H   = 20
cost        = 0.003 / 20 = 0.00015/day   (amortized)
state src   = data/processed/regime/regime.parquet (Z_t per asset)
T_THRESHOLD = DROP
σ_i         = DROP
```

### 1.2 PHASE

1. scripts/backtest_nonoverlap.py 구조 분석 (재사용 판정)
2. scripts/policy/build_signal_v6.py 작성
3. backtest 실행 (Sharpe / Calmar / MDD)
4. v3/v4 baseline 비교 (Sharpe 1.806 / Calmar 2.473 / MDD -22.96%)
5. COMMIT + tag v6.0

### 1.3 산출

```
scripts/policy/build_signal_v6.py
data/processed/policy/signal_v6.parquet
data/processed/backtest_v6/{daily_portfolio, trades, summary}
HANDOFF_v6.md
tag v6.0
```

---

## 2. v6.5 — Calibration GATE (BINARY)

### 2.1 점검 항목

```
[CAL-1] parameter stability
        regime label_map / T_star: seed 변동 시 변화율
        threshold: 변화율 < 5%

[CAL-2] turnover distribution
        annual implied cost = annual turnover × 0.003
        threshold: implied cost < 0.03/year (3% drag)

[CAL-3] state occupancy drift
        Z_t 분포 year-by-year 변화
        i=4 (E=88bps, N=8,638) 안정성
        threshold: shift < 15%

[CAL-4] candidate count distribution
        daily K = |candidates|
        K=0 일자 비율
        threshold: K=0 일자 < 5% of trading days
```

⚠ threshold 값들은 v6.5 진입 시 사용자 명시 가능. default 위 값 사용.

### 2.2 DECISION RULE (binary, no partial pass)

```
v6.5_DECISION_RULE:

PASS ONLY IF:
    CAL-1 PASS
AND CAL-2 PASS
AND CAL-3 PASS
AND CAL-4 PASS

ELSE:
    FAIL (NO EXCEPTION)

→ v6.5 = binary gate (no partial pass, no weighting)
```

### 2.3 산출

```
scripts/calibration/calib_v6.py
data/processed/calibration/{stability, turnover, occupancy, candidates}.parquet
reports/calibration_v6.md (PASS/FAIL + 정량 결과 4종)
```

### 2.4 진입 조건

v6.0 commit 완료 후.

### 2.5 FAIL 시 처리

```
v6 parameter freeze 또는 spec 조정 후 재진입.
v7 진입 차단.
```

---

## 3. v7 — Walk-Forward Robustness

### 3.1 CV 정의

```
[CV-A] time-block CV
       - 6 annual folds (v3/v4 baseline 호환)
       - 시간 순서 보존, no leakage
       - per-fold: Sharpe, Calmar, MDD

[CV-B] regime-block CV
       - bull / bear / shock regime 비례 보존
       - 단일 regime fold 회피
       - regime-conditional Sharpe

[CV-C] 2022 fold 정밀 분석
       - 사용자 memory: 2022 bear fold 약점 known
       - PnL 분해 (state / regime / cost 기여도)
       - 손실 원인 isolate
```

### 3.2 AGGREGATION RULE

```
v7_AGGREGATION_RULE:

primary metric   : mean Sharpe across 6 folds
secondary metric : worst-fold Sharpe (risk floor)

PASS ONLY IF:
    mean Sharpe       >  baseline (1.806)
AND worst-fold Sharpe >  0
AND pass_folds        >= 4/6

→ "평균 좋지만 단일 fold 붕괴" 케이스 차단
```

### 3.3 baseline 비교

```
v3/v4 baseline (NEXT_SESSION.md §1.4):
    Sharpe       : 1.806 (single split)
    pass_folds   : 3/6
    CV           : 1.21

v7 target:
    pass_folds   : >= 4/6 (improvement 1+)
    CV           : < 1.21
    mean Sharpe  : > 1.806
```

### 3.4 산출

```
scripts/validation/walk_forward_v7.py
data/processed/walk_forward_v7/{folds, summary, regime_breakdown}.parquet
reports/walk_forward_v7.md (PASS/FAIL + aggregation result)
```

### 3.5 진입 조건

v6.5 ALL PASS.

---

## 4. v8 — Risk Regime Extension (BRANCH POINT)

### 4.1 DEFAULT

```
long-only 유지 → v8-A 자동 진입
```

### 4.2 BRANCH CONDITION (v8-B 진입 조건)

```
v8_BRANCH_CONDITION:

IF v7 result :
    pass_folds       >=  4/6
AND CV               <   1.0
AND worst_MDD        >   THRESHOLD_MDD
AND turnover         stable (v6.5 CAL-2 PASS)
AND user_explicit    =   "long-short consideration"
THEN
    allow v8-B (long-short evaluation)
ELSE
    remain v8-A (long-only default)

⚠ THRESHOLD_MDD 결정 필요 [PEND-3]
   v3/v4 baseline MDD = -22.96% → -25% threshold 시 거의 fail
   options:
     -20% (엄격, baseline 대비 개선 요구)
     -25% (현재 안, 관대)
     "baseline 대비 상대 개선 > 10%" (상대 기준)
   → v8 진입 시 명시 필요
```

### 4.3 v8-A : long-only + bear hedge

```
[A.1] bear regime classifier
      - state-level signal (i=2: E=-13.93, i=6: -4.15, i=7: -1.87)
      - aggregate bear score
      - threshold 결정

[A.2] exposure rule
      - bear detected: position scale = 0 (full cash) OR ∈ [0, 1]
      - drawdown threshold-based exposure reduction

[A.3] 2022 fold 개선 검증
      - max drawdown 개선
      - Calmar ratio 개선
```

### 4.4 v8-B : long-short (override only)

```
조건 충족 시에만 진입.
- {-1, 0, +1} action space
- short cost model (대주 비용 + 차입 비용)
- 사용자 memory "long-only" classification 변경 (명시 동의 필요)
- 신규 risk model
- HANDOFF_v8b.md 별도 작성 (v8-A 와 분기 명시)
```

### 4.5 산출 (A branch default)

```
scripts/risk/bear_regime_v8.py
scripts/policy/build_signal_v8.py (v6 + bear filter)
data/processed/backtest_v8/
HANDOFF_v8.md
```

### 4.6 진입 조건

v7 PASS + branch decision.

---

## 5. v9 — Productionization

### 5.1 구성

```
[PROD-1] data pipeline
         - scripts/fetch_daily_v2.py 활용
         - daily KRX close 후 자동 fetch
         - panel.parquet 증분 update
         - integrity check (universe 262 유지)

[PROD-2] signal pipeline
         - daily Z_t computation
         - signal_v6 또는 v8 산출
         - latency: T-day close → T+1 open

[PROD-3] execution layer (분리)
         - signal → order 변환은 별도 시스템
         - slippage model 고정 (VWAP 가정 등)
         - order timing rule
         - partial fill handling

[PROD-4] paper trading
         - production 전 검증
         - 실시간 signal vs 실제 시장가
         - daily PnL reconciliation

[PROD-5] production deployment
         - 매일 자동 실행 (cron / Airflow)
         - alerts: signal anomaly, data gap, execution failure
         - audit log: signal/order/fill timestamp
```

### 5.2 PAPER TRADING PASS 기준 [PEND-4]

```
⚠ v9 진입 시 결정 필요:

duration   : ? trading days
             options: 30 / 60 / 90 (default 권장: 60)

metric     : daily PnL reconciliation 오차 < ? bps
             options: 5bps / 10bps / 20bps (default 권장: 10bps)

FAIL 시    : production 진입 차단
             → execution layer 재작성 또는 v6 revision
```

### 5.3 산출

```
scripts/production/daily_pipeline.py
scripts/production/execution_interface.py
data/production/{signals, orders, fills, pnl}/
HANDOFF_v9.md (운용 매뉴얼 포함)
```

### 5.4 진입 조건

v8 결정 완료 + paper trading 통과.

---

## 6. v10 — Monitoring / Lifecycle

### 6.1 핵심 구분

```
drift  = model failure        → retrain trigger
regime = market state change  → 정상 동작 (retrain 금지)

→ 둘 구분 안 하면 false retrain (regime change 시점 retrain = 최악)
```

### 6.2 DRIFT 정의 (정량)

```
DRIFT CONDITION (any of):
    PSI(signal distribution)        >  0.2
    OR KS-test p-value              <  0.01 (5-day rolling)
    OR state occupancy shift         >  15%

EXCLUSION:
    regime change flag active → drift signal ignore
    → retraining NOT triggered
```

### 6.3 REGIME CHANGE FLAG 정의 [PEND-5]

```
⚠ v10 spec 작성 시 결정 필요:

option A: stationary π 의 5-day MA vs 60-day baseline
          차이 > 10% → regime change flag = TRUE

option B: dominant state 변경
          (예: i=5 SHOCK 우세 → i=0 우세로 전환)

option C: ChatGPT/Claude 별도 spec 작성

default 권장 : option A (정량 명확)
```

### 6.4 감시 항목

```
[MON-1] signal drift detection (§6.2 정량 정의)
[MON-2] regime stability monitoring (vs historical baseline)
[MON-3] PnL attribution (state / regime / cost / slippage)
[MON-4] retraining trigger
        조건: drift AND not regime change
        scope: build_regime.py 재실행 OR v6 spec 재조정
        자동 vs 수동: default 수동 confirm
[MON-5] system lifecycle
        quarterly review: parameter stability
        annual rebuild: universe 262 재선정
        major event: explicit re-spec (v11+)
```

### 6.5 산출

```
scripts/monitoring/{drift, regime_change, attribution, retrain}.py
data/monitoring/{daily_health, alerts}.parquet
reports/monthly_review_*.md
HANDOFF_v10.md (operating procedure)
```

---

## 7. 단계 간 결정 timing

```
v6 진입 전     V6_ENTRY.md §2 spec lock 확인       (다음 세션)
v6.5 진입 전   v6.0 backtest + tag v6.0 완료
v7 진입 전     v6.5 ALL 4 CAL PASS
v7 → v8        ⚠ branching decision
                 default = v8-A (long-only)
                 v8-B = explicit override only + THRESHOLD_MDD 결정 [PEND-3]
v8 → v9        backtest + walk-forward 통과
v9 → v10       paper trading 통과 (duration + tolerance 결정 [PEND-4])
v10 진입       regime change flag 정의 [PEND-5]
```

---

## 8. PENDING DECISIONS

진입 시점에 결정 필요한 항목:

```
[PEND-1] v6.5 default threshold 4종 변경 여부
         (CAL-1: 5%, CAL-2: 3%/year, CAL-3: 15%, CAL-4: 5%)
         진입 시점: v6.5 진입

[PEND-2] v7 baseline 비교 기준 변경 여부
         (mean Sharpe > 1.806, pass_folds >= 4/6, CV < 1.21)
         진입 시점: v7 진입

[PEND-3] v8 THRESHOLD_MDD 결정
         (-20% / -25% / baseline 대비 상대)
         진입 시점: v8 진입 + branch decision

[PEND-4] v9 paper trading 기준
         (duration 30/60/90, tolerance 5/10/20 bps)
         진입 시점: v9 진입

[PEND-5] v10 regime change flag 정의
         (option A 권장 / B / C)
         진입 시점: v10 spec 작성

[PEND-6] §2.1 RETAINED release 정식 §14 unlock block 작성
         (v5 §2.2 carry, formalization)
         진입 시점: v6 HANDOFF 또는 v7 HANDOFF
```

---

## 9. 작업 분리 원칙

```
연구 단계 (v6, v6.5, v7, v8):
  - Claude 응답 효율 우선
  - 단일 Claude 세션 권장 (cross-AI deadlock 회피)
  - 각 단계 완료 시 HANDOFF_v*.md + tag
  - 세션 토큰 60% 도달 시 종료 + 다음 세션 진입

운용 단계 (v9, v10):
  - production code review 우선
  - 사용자 직접 운용 (자동화 후)
  - Claude 역할: monitoring spec 작성 + alert 분석 보조
```

---

## 10. 다음 세션 첫 메시지

```
github.com/stanleyim/super 의
V6_ENTRY.md + HANDOFF_v5.md + ROADMAP_v6_v10.md 정독.
V6 START. spec lock 적용 (V6_ENTRY.md §2). Phase 1 진행.
```

---

## END

본 ROADMAP 은 v6 ~ v10 전 단계 reference.
변경 사항 발생 시 본 파일 갱신 + commit (atomic).
ChatGPT/Claude 양측 동일 reference 사용.
