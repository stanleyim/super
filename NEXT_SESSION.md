# MSM — Next Session TODO

## 현재 상태
- STEP 1~9 완료
- 단일 split (2023~test): Sharpe 1.81, Calmar 2.47, MDD -23%
- Walk-forward 6 folds: **3/6 PASS (FAIL)** — CV 1.21, 2022 bear loss -0.97
- SMA-120 overlay: **역효과 확인** (CV 1.21→2.91) → 폐기
- **결론**: MSM v1 = long-only momentum, regime-dependent (bull market only)

## 핵심 스크립트
- fetch_daily_v2.py — KRX ingestion (datetime64, year boundary fix)
- build_state_vector.py — STEP 2~4 (K=6, 4 features → 1296 states)
- build_transition.py — STEP 5~6 (regime + P_global + P_by_regime)
- build_edge.py — STEP 7~8 (edge field + tradeable filter)
- backtest.py — h=1 baseline
- horizon_sensitivity.py — h*=20 확인 (Sharpe peak at h=20)
- backtest_nonoverlap.py — h=20 final (Sharpe 1.81)
- walk_forward.py — 6 folds (3/6 FAIL)
- walk_forward_overlay.py — overlay 무효 확인 (보존용)

## 출력 위치
data/processed/
  state_vector/         (577,311 rows)
  transition/           (state_table, P_*, panel_with_regime)
  edge/                 (edge_table, tradeable: 32 states)
  backtest/
    h20_nonoverlap/     (Sharpe 1.81)
    walk_forward/       (3/6 FAIL)
    walk_forward_overlay/  (SMA 무효)

## LOCKED 파라미터
- universe: 262 fixed (scripts/universe_262.json)
- K=6, features=[z_r, z_sigma, z_v, z_flow] → 1296 states
- W_sigma=20, W_z=252 (causal)
- horizon: h=20
- cost_rt: 0.003 (0.3% round-trip)
- MIN_VISITS=100, T_THRESHOLD=2.0
- regime ∈ {TREND, RANGE}

## 무효 확정
- SMA-120 universe-mean overlay (timing fix 불가)
- threshold tuning (overfit risk)

## 다음 세션 선택지 (우선순위)

### Option 1: 결과 인정, 종결
- "Bull market momentum extractor"로 정의
- 거시 판단은 사람이 + 종목 선정만 시스템 사용

### Option 2: Market-neutral 재설계 (B안)
- 새 노트북 필수
- long top-k + short bottom-k
- daily cross-sectional ranking, beta ≈ 0
- 예상 코드 ~400줄
- KR short 제약 회피 (universe 내 ranking)

### Option 3: SHORT side 추가 (A안)
- 새 노트북
- mu_r < 0 states 식별
- KR short 제약 검토 필요 (차입공매도, uptick rule)
- 예상 코드 ~200줄

### Option 4: 현재 시스템 분석 deepen (코드 추가 없음)
- regime별 trade 분해
- state-level contribution
- 인사이트 추출

## 권고
Option 1 또는 Option 2
