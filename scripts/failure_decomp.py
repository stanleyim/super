"""
failure_decomp.py — MSM Option 4: Failure Topology Mapping

PURPOSE
  Decompose MSM v1 failure (3/6 walk-forward FAIL, 2022 bear -0.97) into:
    A. Regime-level PnL          (macro)
    B. State-level contribution  (micro alpha attribution)
    C. Transition drift          (non-stationarity detection)
    D. State class               (action mapping for Option 2)
    E. EV flip map               (short-side candidate selector)

LOCKED DESIGN
  - Regime: DD-based 3-state FSM (BULL/BEAR/RECOVERY)
    enter BEAR at DD<=-10%, exit BEAR at DD>=-5%, return BULL at new peak
  - Reference: universe-mean equal-weight log-return baseline
  - EV flip statistic: Welch's t (visit-weighted, closed-form)
  - Trade regime: entry_date regime (no lookahead)
  - Core rules: no lookahead, no hash, adjacency preserved
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

# ============================================================
# CONFIG — LOCKED (do not tune without re-running entire pipeline)
# ============================================================
ROOT          = Path(__file__).resolve().parents[1]
DIR_STATE     = ROOT / "data/processed/state_vector"
DIR_BACKTEST  = ROOT / "data/processed/backtest/h20_nonoverlap"
DIR_OHLCV     = ROOT / "data/raw/ohlcv"             # fallback close source
DIR_OUT       = ROOT / "data/processed/failure"
DIR_OUT.mkdir(parents=True, exist_ok=True)

# >>> CONFIRM C1: trades.parquet column names
COL_ENTRY = "entry_date"
COL_EXIT  = "exit_date"
COL_CODE  = "code"
COL_STATE = "state_id"
COL_PNL   = "ret_net"

# Regime FSM thresholds (LOCKED, Q1=(a))
DD_ENTER_BEAR = -0.10
DD_EXIT_BEAR  = -0.05
DD_NEW_PEAK   =  0.00

# Statistical thresholds
MIN_VISITS_PER_REGIME = 30
T_SIG = 2.0
EPS   = 1e-12

# Annualization (h=20 non-overlapping, 252 td/yr)
ANN_FACTOR = np.sqrt(252 / 20)


# ============================================================
# A. REGIME ENGINE — universe-mean DD-based 3-state FSM
# ============================================================
def build_universe_mean_equity(panel_close: pd.DataFrame) -> pd.Series:
    """Equal-weight log-return cumulant. Causal (uses only data up to t)."""
    p = panel_close.pivot(index="date", columns="code", values="close").sort_index()
    log_ret = np.log(p).diff()
    r_market = log_ret.mean(axis=1, skipna=True).fillna(0.0)
    return np.exp(r_market.cumsum()).rename("equity_market")


def drawdown_series(equity: pd.Series) -> pd.Series:
    return (equity / equity.cummax() - 1.0).rename("dd")


def regime_fsm(dd: pd.Series) -> pd.Series:
    """3-state FSM with hysteresis. Uses only DD_t and prev state (strict causal)."""
    labels = np.empty(len(dd), dtype=object)
    cur = "BULL"
    for i, x in enumerate(dd.values):
        if   cur == "BULL"     and x <= DD_ENTER_BEAR: cur = "BEAR"
        elif cur == "BEAR"     and x >= DD_EXIT_BEAR:  cur = "RECOVERY"
        elif cur == "RECOVERY" and x <= DD_ENTER_BEAR: cur = "BEAR"      # relapse
        elif cur == "RECOVERY" and x >= DD_NEW_PEAK:   cur = "BULL"
        labels[i] = cur
    return pd.Series(labels, index=dd.index, name="regime")


def build_regime_labels(panel_close: pd.DataFrame) -> pd.DataFrame:
    eq = build_universe_mean_equity(panel_close)
    dd = drawdown_series(eq)
    rg = regime_fsm(dd)
    return pd.concat([eq, dd, rg], axis=1).reset_index()


# ============================================================
# B. REGIME-LEVEL PNL (macro)
# ============================================================
def compute_regime_pnl(trades: pd.DataFrame, regime_labels: pd.DataFrame) -> pd.DataFrame:
    t = trades.merge(
        regime_labels[["date", "regime"]].rename(columns={"date": COL_ENTRY}),
        on=COL_ENTRY, how="left"
    )
    g = t.groupby("regime")[COL_PNL]
    out = pd.DataFrame({
        "n_trades": g.size(),
        "mean":     g.mean(),
        "std":      g.std(ddof=1),
        "sum":      g.sum(),
        "hit_rate": (t.groupby("regime")[COL_PNL].apply(lambda s: (s > 0).mean())),
    })
    out["sharpe_ann"] = out["mean"] / (out["std"] + EPS) * ANN_FACTOR
    return out.reset_index()


# ============================================================
# C. STATE-LEVEL DECOMPOSITION (state × regime cell stats)
# ============================================================
def compute_state_decomp(trades: pd.DataFrame, regime_labels: pd.DataFrame) -> pd.DataFrame:
    t = trades.merge(
        regime_labels[["date", "regime"]].rename(columns={"date": COL_ENTRY}),
        on=COL_ENTRY, how="left"
    )
    g = t.groupby([COL_STATE, "regime"])[COL_PNL]
    out = pd.DataFrame({
        "n":    g.size(),
        "mean": g.mean(),
        "std":  g.std(ddof=1).fillna(0.0),
        "sum":  g.sum(),
    }).reset_index()
    out["se"]           = out["std"] / np.sqrt(out["n"].clip(lower=1))
    out["t_one_sample"] = out["mean"] / (out["se"] + EPS)   # H0: mu=0
    return out


# ============================================================
# D. TRANSITION DRIFT (P(s'|s | regime), KL divergence)
# ============================================================
def compute_transition_drift(panel: pd.DataFrame, regime_labels: pd.DataFrame) -> pd.DataFrame:
    p = panel[["date", "code", COL_STATE]].sort_values(["code", "date"]).copy()
    p["next_state"] = p.groupby("code")[COL_STATE].shift(-1)
    p = p.dropna(subset=["next_state"])
    p[COL_STATE]     = p[COL_STATE].astype(np.int64)
    p["next_state"]  = p["next_state"].astype(np.int64)
    p = p.merge(regime_labels[["date", "regime"]], on="date", how="left")

    counts = (p.groupby(["regime", COL_STATE, "next_state"]).size()
                .rename("n").reset_index())
    totals = counts.groupby(["regime", COL_STATE])["n"].transform("sum")
    counts["P"] = counts["n"] / totals.clip(lower=1)
    return counts


def kl_bull_vs_bear(drift: pd.DataFrame) -> pd.DataFrame:
    """KL( P_bull(.|s) || P_bear(.|s) ) per state. Laplace-smoothed on BEAR."""
    a = drift[drift["regime"]=="BULL"].rename(columns={"n":"n_b","P":"P_b"})
    b = drift[drift["regime"]=="BEAR"].rename(columns={"n":"n_e","P":"P_e"})
    m = a.merge(b[[COL_STATE,"next_state","n_e"]],
                on=[COL_STATE,"next_state"], how="outer").fillna(0.0)
    K = m["next_state"].nunique()
    m["n_e_total"]   = m.groupby(COL_STATE)["n_e"].transform("sum")
    m["P_e_smooth"]  = (m["n_e"] + 1) / (m["n_e_total"] + K)            # Laplace
    m["P_b"]         = m["P_b"].fillna(0.0)
    m["kl_term"]     = np.where(m["P_b"] > 0,
                                m["P_b"] * np.log((m["P_b"]+EPS) / (m["P_e_smooth"]+EPS)),
                                0.0)
    return (m.groupby(COL_STATE)["kl_term"].sum()
              .rename("kl_bull_bear").reset_index())


# ============================================================
# E. EV FLIP MAP — Welch's t per state
# ============================================================
def compute_ev_flip_map(state_decomp: pd.DataFrame) -> pd.DataFrame:
    bull = state_decomp[state_decomp["regime"]=="BULL"].set_index(COL_STATE)
    bear = state_decomp[state_decomp["regime"]=="BEAR"].set_index(COL_STATE)
    common = bull.index.intersection(bear.index)
    if len(common) == 0:
        return pd.DataFrame(columns=[COL_STATE,"mu_bull","mu_bear","t_flip","reliable"])

    out = pd.DataFrame(index=common)
    out["mu_bull"]    = bull.loc[common, "mean"]
    out["mu_bear"]    = bear.loc[common, "mean"]
    out["n_bull"]     = bull.loc[common, "n"]
    out["n_bear"]     = bear.loc[common, "n"]
    out["s2_bull"]    = bull.loc[common, "std"] ** 2
    out["s2_bear"]    = bear.loc[common, "std"] ** 2
    se = np.sqrt(out["s2_bull"] / out["n_bull"].clip(lower=1)
               + out["s2_bear"] / out["n_bear"].clip(lower=1))
    out["t_flip"]     = (out["mu_bull"] - out["mu_bear"]) / (se + EPS)
    out["t_bull_pos"] = bull.loc[common, "t_one_sample"]
    out["t_bear_pos"] = bear.loc[common, "t_one_sample"]
    out["reliable"]   = (out["n_bull"] >= MIN_VISITS_PER_REGIME) & \
                        (out["n_bear"] >= MIN_VISITS_PER_REGIME)
    return out.reset_index().rename(columns={"index": COL_STATE})


# ============================================================
# F. STATE CLASSIFICATION (action mapping for Option 2)
# ============================================================
def classify_states(ev_flip: pd.DataFrame) -> dict:
    """
    INVARIANT   → long core      (t_bull > +2 AND t_bear > +2)
    CONDITIONAL → regime-gated   (t_bull > +2 AND |t_bear| <= 2)
    TRAP        → short core     (t_bull > +2 AND t_bear < -2)
    DEAD        → drop universe  (t_bull <= 0 AND t_bear <= 0)
    AMBIGUOUS   → review         (else)
    INSUFFICIENT→ low visits     (reliable == False)
    """
    out = {}
    for _, r in ev_flip.iterrows():
        sid = int(r[COL_STATE])
        if not r["reliable"]:
            out[sid] = "INSUFFICIENT"; continue
        tb, te = r["t_bull_pos"], r["t_bear_pos"]
        if   tb >  T_SIG  and te >  T_SIG:        out[sid] = "INVARIANT"
        elif tb >  T_SIG  and te < -T_SIG:        out[sid] = "TRAP"
        elif tb >  T_SIG  and abs(te) <= T_SIG:   out[sid] = "CONDITIONAL"
        elif tb <= 0      and te <= 0:            out[sid] = "DEAD"
        else:                                     out[sid] = "AMBIGUOUS"
    return out


# ============================================================
# HELPERS
# ============================================================
def load_close_fallback() -> pd.DataFrame:
    files = sorted(DIR_OHLCV.glob("*.parquet"))
    df = pd.concat([pd.read_parquet(f, columns=["date","code","close"]) for f in files],
                   ignore_index=True)
    return df.drop_duplicates(["date","code"]).dropna(subset=["close"])


def get_panel_close(panel: pd.DataFrame) -> pd.DataFrame:
    if "close" in panel.columns:
        return panel[["date","code","close"]].dropna()
    return load_close_fallback()


# ============================================================
# MAIN
# ============================================================
def main():
    panel  = pd.read_parquet(DIR_STATE / "panel.parquet")           # CONFIRM C2
    trades = pd.read_parquet(DIR_BACKTEST / "trades.parquet")        # CONFIRM C1

    # sanity
    for col in [COL_ENTRY, COL_CODE, COL_STATE, COL_PNL]:
        assert col in trades.columns, f"trades missing column: {col}"
    assert COL_STATE in panel.columns, f"panel missing column: {COL_STATE}"

    panel_close = get_panel_close(panel)

    # A. regime
    rg = build_regime_labels(panel_close)
    rg.to_parquet(DIR_OUT / "regime_labels.parquet", index=False)

    # B. macro
    macro = compute_regime_pnl(trades, rg)
    macro.to_parquet(DIR_OUT / "regime_pnl.parquet", index=False)

    # C. state × regime
    decomp = compute_state_decomp(trades, rg)
    decomp.to_parquet(DIR_OUT / "state_decomp.parquet", index=False)

    # D. transition drift + KL
    drift = compute_transition_drift(panel, rg)
    drift.to_parquet(DIR_OUT / "transition_drift.parquet", index=False)
    kl    = kl_bull_vs_bear(drift)
    kl.to_parquet(DIR_OUT / "transition_kl.parquet", index=False)

    # E. EV flip map
    flip = compute_ev_flip_map(decomp)
    flip.to_parquet(DIR_OUT / "ev_flip_map.parquet", index=False)

    # F. classification
    cls = classify_states(flip)
    with open(DIR_OUT / "state_class.json", "w") as f:
        json.dump({str(k): v for k, v in cls.items()}, f, indent=2)

    # summary
    print("== REGIME PnL ==")
    print(macro.to_string(index=False))
    print("\n== STATE CLASS ==")
    print(pd.Series(cls).value_counts())
    print(f"\nReliable states (both regimes ≥ {MIN_VISITS_PER_REGIME} visits): "
          f"{int(flip['reliable'].sum())} / {len(flip)}")


if __name__ == "__main__":
    main()
