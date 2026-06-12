# MSM Next Session — Handoff (2026-06-12, post-R1 + STAGE 2 G2)

## 0. ONE-LINE STATUS

main = R1 staged rebuild + STAGE 2 G2 (attribution + diagnostics + viz + observe CLI) deployed.
Latest commit: f6d82c2. STAGE 1 + STAGE 2 + G2 smoke PASS.
Pending: artifact policy lock (strict vs relaxed) + STAGE 3 unlock signal.

---

## 1. CURRENT MAIN STATE (FACTS)

### 1.1 Commit history (top 5)
```
f6d82c2 fix(artifact): restore trades.parquet via R1 staged rebuild
4e7dd19 feat(observation): STAGE 1 - read-only observation layer scaffold
1a818c2 data(failure): regenerate analytics artifacts on long-only main
41e5c66 fix(failure_decomp): macro_regime rename (isolated bug fix)
4072e3b Revert "Merge pull request #1 from stanleyim/feat/msm-v1-dual-side-investigation"
```

### 1.2 Pipeline DAG (verified by execution this session)
```
data/raw/ohlcv/year=*.parquet                          (13 files, 2014~2026)
        v
scripts/build_state_vector.py                          (LOCKED)
        v
data/processed/state_vector/year=*.parquet             (12 files, tracked)
        v
scripts/build_transition.py                            (LOCKED)
        v
data/processed/transition/
  state_table.parquet                                  (UNTRACKED, regen-only)
  transition_long.parquet                              (UNTRACKED, regen-only)
  regime_thresholds.json                               (UNTRACKED, regen-only)
  panel_with_regime/year=*.parquet  (12 files)         (UNTRACKED, regen-only)
        v
scripts/backtest_nonoverlap.py                         (LOCKED)
        v
data/processed/backtest/h20_nonoverlap/
  trades.parquet                  (5,593 rows)         (tracked)
  daily_portfolio.parquet                              (tracked)
  summary.json                                         (tracked)
        v
scripts/observation/  (STAGE 1 + STAGE 2 G2)
  loader.py / classify.py                              (STAGE 1)
  attribution.py / diagnostics.py / viz.py / observe.py(STAGE 2)
        v
data/processed/observation/
  attribution.parquet
  attribution_summary.json
  diagnostics_kl_topN.json
  drift_report.json

reports/
  regime_pnl.png
  class_distribution.png
  kl_topN.png
  run_logs/{A_state_vector,B_transition,C_backtest}.log
```

### 1.3 R1 execution timings (this session)
```
STAGE A (build_state_vector)  : 7.1s
STAGE B (build_transition)    : 3.2s
STAGE C (backtest_nonoverlap) : 4.8s
TOTAL R1                      : ~15.1s
```

### 1.4 Reproducibility check (vs prior session)
```
prior session : Sharpe 1.81,  Calmar 2.47,  MDD -23%
this session  : Sharpe 1.806, Calmar 2.473, MDD -22.96%
final_equity  : 4.6935x  /  CAGR 56.77%
=> deterministic kernel verified (sub-percent agreement)
```

### 1.5 Regime distribution (1,296 states)
```
SHOCK      : 150
TREND      : 197
RANGE      : 232
TRANSITION : 717
populated  : 1296/1296
```

### 1.6 State class distribution (84 tradeable)
```
INSUFFICIENT : 59
CONDITIONAL  :  8
INVARIANT    :  4   (state_id in {14, 266, 606, 952})
AMBIGUOUS    : 13
DEAD         :  0
TRAP         :  0
```

---

## 2. LOCKED DECISIONS (CARRY-FORWARD)

### STAGE 2 design lock
```
D1 = both       (ret_net + ret_gross)
D2 = split      (data/processed/observation/ + reports/)
D3 = 50         (KL top-N)
D4 = argparse   (stdlib only)
D5 = c          (smoke = pipeline + CLI subprocess)
D6 = whitelist  (reports/*.png)
D7 = no paste   (NEXT_SESSION.md regenerated each handoff)
```

### Schema lock (final)
```
attribution_summary.json keys = {
  total_pnl, ret_net, ret_gross,
  pnl_by_regime, pnl_by_state, pnl_by_asset,
  top_contributors, worst_contributors
}
drift_report.json keys = {
  kl_topN, p_stay, transition_shift_matrix,
  regime_frequency_change, state_distribution_shift
}
```

### G2 invariants (no schema change)
- attribution.py / diagnostics.py: `_assert_finite()` on all loader outputs
- `json.dumps(allow_nan=False)` on all summary/report files
- smoke: recursive finite check on JSON + numpy.isfinite on parquet

### LOCKED kernel (NO modification under any circumstance)
```
scripts/build_state_vector.py
scripts/build_transition.py
scripts/backtest_nonoverlap.py
+ scripts/observation/*  (post-G2)
```

### LOCKED parameters (MSM v1)
```
K              = 6
N_STATES       = 1296   (K^4)
features       = [z_r, z_sigma, z_v, z_flow]
W_sigma        = 20
W_z            = 252
shift          = 1      (causal)
H              = 20     (holding horizon)
cost_rt        = 0.003
MIN_VISITS     = 100
T_THRESHOLD    = 2.0
TRADEABLE_REG  = {TREND, RANGE}
```

---

## 3. OPEN POLICY DECISION (SINGLE BLOCKING ITEM)

### Background
Commit f6d82c2 message claimed "WHITELIST POLICY: minimal (trades.parquet only)", but
actual `.gitignore` patch used directory-level whitelists, resulting in:
```
ACTUALLY TRACKED beyond "trades only":
  daily_portfolio.parquet, summary.json
  state_vector/year=*.parquet (12 files)
  reports/run_logs/*.log (3 files)
  observation/* artifacts (4 files)
  reports/*.png (3 files)
```
=> Current state = R3-relaxed (NOT R3-strict).

### Decision required
```
(P-strict)   restore minimal whitelist
             - .gitignore: add explicit ignore for
                 data/processed/backtest/h20_nonoverlap/daily_portfolio.parquet
                 data/processed/backtest/h20_nonoverlap/summary.json
                 data/processed/state_vector/year=*.parquet
                 reports/run_logs/*.log
             - git rm --cached on those files
             - new commit
             - fresh-clone cost: ~15s R1 rerun

(P-relaxed)  formalize current state
             - no code/repo change
             - lock update: WHITELIST = full pipeline outputs
             - prior commit message text noted as inaccurate (historical record)

(P-hold)     defer decision
             - no action; revisit when context warrants
```

Fact-based note (not directive): P-relaxed = lowest immediate risk; P-strict = enforces
declared policy at minor fresh-clone cost; P-hold = valid until next material change.

---

## 4. NEXT-SESSION EXECUTION PROTOCOL

### 4.1 Mandatory setup cell (fresh notebook)
```python
import os
from pathlib import Path
from google.colab import userdata

GH_TOKEN = userdata.get("GH_TOKEN"); assert GH_TOKEN
os.environ["GH_TOKEN"] = GH_TOKEN
os.environ["GIT_TERMINAL_PROMPT"] = "0"
!git config --global user.name  "colab-bot"
!git config --global user.email "colab@bot.local"

os.chdir("/content")
if Path("/content/super/.git").exists():
    os.chdir("/content/super"); !git pull origin main
else:
    !git clone https://$GH_TOKEN@github.com/stanleyim/super.git
    os.chdir("/content/super")
print("READY:", Path(".git").exists())
!git log --oneline -3
```
Expected HEAD: f6d82c2 (or later if subsequent commits).

### 4.2 Smoke gate (before any new work)
```python
!python tests/observation_smoke.py
```
Must show: `=== OK ===`. If FAIL -> diagnose before proceeding.
Common failure modes:
  - loader.load_* FileNotFoundError -> run R1 (4.3)
  - [G2] non-finite                 -> upstream data corruption
  - schema KeyError                 -> STAGE 2 module/schema drift

### 4.3 R1 rebuild (only if upstream artifacts missing)
Staged execution mandatory (NOT single-cell). A -> verify -> B -> verify -> C -> verify.
Total ~15s. Cells preserved in chat history of this session.

### 4.4 STAGE 2 entrypoints (read-only, safe)
```
python scripts/observe.py build      # rebuild attribution + diagnostics + viz
python scripts/observe.py summary    # totals + by_regime
python scripts/observe.py class      # state class distribution
python scripts/observe.py regime     # PnL by regime
python scripts/observe.py drift      # drift report summary
```

---

## 5. STAGE 3 ENTRY GATE (LOCKED — DO NOT CROSS WITHOUT SIGNAL)

### 5.1 STAGE 3 scope (specification ONLY)
```
S3-A) EV surface construction
       E[R | S_t, regime] tensor over 1296 x 4 grid
       built from state_decomp.parquet + ev_flip_map.parquet
       validated via t_one_sample, t_flip thresholds

S3-B) Tradeable mask
       M(S_t) = 1  iff
         EV(S_t) > 0
         AND visits >= MIN_VISITS
         AND |t_one_sample| >= T_THRESHOLD
         AND state_class in {INVARIANT, CONDITIONAL}
         AND regime in TRADEABLE_REG
       output: tradeable_mask.parquet

S3-C) Transition filtering
       drop states with kl_bull_bear > Q90 AND p_stay < 0.5
       output: stable_states.parquet

S3-D) Edge field normalization
       cross-asset z-score of EV per regime
       output: edge_field.parquet
```

### 5.2 STAGE 3 unlock signal (REQUIRED)
Explicit user statement of:
  "STAGE 3 UNLOCK: S3-A" / "S3-B" / "S3-C" / "S3-D" / "ALL"
+ confirmation of LOCKED parameter scope (no kernel modification)
+ output destination policy (proposed: data/processed/edge/)
+ schema spec for each new artifact

### 5.3 STAGE 3 forbidden until unlock
- no EV inference
- no tradeable region computation
- no edge field generation
- no new module under scripts/edge/ or similar
- no .gitignore changes for edge artifacts
- no spec doc creation (docs/STEP4_SPEC.md or similar)

---

## 6. HARD CONSTRAINT LOCK (operative for next session)

```
[L1] No speculation. If a fact is not in repo or this handoff, ASK.
[L2] No auto-fill. Missing parameters require explicit user lock.
[L3] No LOCKED kernel modification (build_state_vector / build_transition /
     backtest_nonoverlap / observation modules post-G2).
     Execution of LOCKED scripts is PERMITTED; code changes are NOT.
[L4] No STAGE 3 work without §5.2 unlock signal.
[L5] No structural changes to observation/* schema (8 attr keys, 5 drift keys).
[L6] No automatic git commit/push. Every commit requires explicit user confirmation
     of (a) message text, (b) staged file set, (c) target branch.
[L7] No assumption about user's local filesystem. Verify before proposing paths.
[L8] Read-only inspection (file viewing, grep, ls, git log) is always permitted.
     Execution and writes are NOT.
[L9] On failure, STOP. Report stderr + log path + diagnosis. Do not retry,
     auto-fix, or branch into alternatives without user direction.
```

---

## 7. KNOWN ISSUES (carry-forward, non-blocking)

```
[K1] commit f6d82c2 message inaccurate re: whitelist scope
     impact: history record only, no functional impact
     resolution: addressed by §3 decision

[K2] reports/run_logs/*.log tracked in main
     impact: log files persist in repo history
     resolution: subset of P-strict

[K3] daily_portfolio.parquet, summary.json tracked despite "trades only" intent
     impact: minor repo bloat, fresh-clone faster
     resolution: subset of P-strict

[K4] STAGE 2 viz.py is failure-tolerant (per-chart try/except)
     impact: silent partial failure possible
     mitigation: smoke asserts >=1 chart succeeds, not all
     reconsider: escalate to hard-fail if any chart consistently fails
```

---

## 8. CONTACT POINTS FOR NEXT SESSION

PRIMARY ARTIFACTS:
  data/processed/backtest/h20_nonoverlap/trades.parquet
  data/processed/observation/attribution_summary.json
  data/processed/observation/drift_report.json

ENTRY POINTS:
  python tests/observation_smoke.py
  python scripts/observe.py {build,summary,class,regime,drift}

DOCS:
  docs/STEP3_SPEC.md     (observation layer spec)
  NEXT_SESSION.md        (this file)

LOGS:
  reports/run_logs/A_state_vector.log
  reports/run_logs/B_transition.log
  reports/run_logs/C_backtest.log

---

## 9. ONE-LINE DIRECTIVE FOR NEXT CLAUDE

> Read this file in full. Verify §1 facts against repo before acting.
> Do not speculate. Do not extend scope. Do not unlock STAGE 3 without explicit signal.
> Every action requires user confirmation unless it is read-only inspection.

---
_End of handoff._
