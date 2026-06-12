# MSM Step 3 - Observation-Only Architecture Spec

## 1. Layering

- EXECUTION LAYER (LOCKED): scripts/backtest_nonoverlap.py produces trades.parquet
- STATE LAYER (LOCKED): build_state_vector / build_transition produces state_vector, transition
- OBSERVATION LAYER: failure_decomp + scripts/observation/ (read-only consumer)

Forbidden: observation/* importing execution/state code; mutating artifacts.

## 2. Artifact Schemas

- state_class.json       : dict state_id to class in INVARIANT/CONDITIONAL/TRAP/DEAD/AMBIGUOUS/INSUFFICIENT
- regime_pnl.parquet     : macro_regime, n_trades, mean, std, sum, hit_rate, sharpe_ann
- state_decomp.parquet   : state_id, macro_regime, n, mean, std, sum, se, t_one_sample
- ev_flip_map.parquet    : state_id, mu_bull, mu_bear, n_bull, n_bear, s2_bull, s2_bear, t_flip, t_bull_pos, t_bear_pos, reliable
- regime_labels.parquet  : date, equity_market, dd, regime (BULL/BEAR/RECOVERY)
- transition_drift.parquet: regime, state_id, next_state, n, P
- transition_kl.parquet  : state_id, kl_bull_bear
- panel.parquet          : date, code, state_id, close, ...
- trades.parquet         : entry_date, exit_date, code, state_id, regime, ret_gross, ret_net

## 3. Modules

- loader.py    : read-only artifact loading + hard-fail schema validation
- classify.py  : state_id to class query
- attribution.py (STAGE 2): PnL decomposition
- diagnostics.py (STAGE 2): transition instability
- viz.py (STAGE 2)        : matplotlib charts
- observe.py (STAGE 2)    : CLI

## 4. Non-Functional Requirements

- N1 read-only filesystem
- N2 no execution feedback
- N3 LOCKED parameters untouched
- N4 deterministic
- N5 hard-fail schema validation
