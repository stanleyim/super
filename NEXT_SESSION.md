# MSM — Next Session TODO

## 현재 상태
- STEP 1~9 완료
- 단일 split (2023~test): Sharpe 1.81, Calmar 2.47, MDD -23%
- Walk-forward 6 folds: **3/6 PASS (FAIL)** — CV 1.21, 2022 bear loss -0.97
- SMA-120 overlay: **역효과 확인** (CV 1.21→2.91) → 폐기
- **결론**: MSM v1 = long-only momentum, regime-dependent (bull market only)

## 핵심 스크립트
- `fetch_daily_v2.py` — KRX ingestion (datetime64, year boundary fix)
- `build_state_vector.py` — STEP 2~4 (K=6, 4 features → 1296 states)
- `build_transition.py` — STEP 5~6 (regime + P_global + P_by_regime)
- `build_edge.py` — STEP 7~8 (edge field + tradeable filter)
- `backtest.py` — h=1 baseline
- `horizon_sensitivity.py` — h*=20 확인 (Sharpe peak at h=20)
- `backtest_nonoverlap.py` — h=20 final (Sharpe 1.81)
- `walk_forward.py` — 6 folds (3/6 FAIL)
- `walk_forward_overlay.py` — overlay 무효 확인 (보존용)

## 출력 위치
