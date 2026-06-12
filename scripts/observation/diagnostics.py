"""STAGE 2 diagnostics - transition instability + regime drift.

LOCKED: D3 = 50 (KL top-N), D2 = split.
G2:     finite-value guards on loader output + json allow_nan=False.

Output schema (drift_report.json):
  kl_topN, p_stay, transition_shift_matrix,
  regime_frequency_change, state_distribution_shift
"""
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from scripts.observation import loader

OUT_DIR   = Path("data/processed/observation")
OUT_KL    = OUT_DIR / "diagnostics_kl_topN.json"
OUT_DRIFT = OUT_DIR / "drift_report.json"

TOP_N = 50


def _assert_finite(df: pd.DataFrame, cols: Iterable[str], name: str) -> None:
    for c in cols:
        s = df[c]
        if s.isna().any():
            n = int(s.isna().sum())
            raise ValueError(f"[G2] {name}.{c} has {n} NaN row(s)")
        if pd.api.types.is_numeric_dtype(s):
            arr = s.to_numpy()
            if not np.isfinite(arr).all():
                n = int((~np.isfinite(arr)).sum())
                raise ValueError(f"[G2] {name}.{c} has {n} non-finite value(s)")


def _kl_topN() -> list:
    kl = loader.load_transition_kl().copy()
    _assert_finite(kl, ["state_id", "kl_bull_bear"], "transition_kl")
    return (kl.sort_values("kl_bull_bear", ascending=False)
              .head(TOP_N).to_dict(orient="records"))


def _p_stay() -> dict:
    td = loader.load_transition_drift().copy()
    _assert_finite(td, ["state_id", "next_state", "P"], "transition_drift")
    stay = td[td["state_id"] == td["next_state"]]
    out = {}
    for reg, sub in stay.groupby("regime"):
        out[str(reg)] = {int(sid): float(p)
                         for sid, p in zip(sub["state_id"], sub["P"])}
    return out


def _transition_shift_matrix() -> list:
    td = loader.load_transition_drift().copy()
    _assert_finite(td, ["state_id", "next_state", "P"], "transition_drift")
    pivot = td.pivot_table(
        index=["state_id", "next_state"],
        columns="regime", values="P", fill_value=0.0,
    ).reset_index()
    if "BULL" in pivot.columns and "BEAR" in pivot.columns:
        pivot["delta"]     = pivot["BULL"] - pivot["BEAR"]
        pivot["abs_delta"] = pivot["delta"].abs()
        top = (pivot.sort_values("abs_delta", ascending=False)
                    .head(TOP_N).drop(columns=["abs_delta"]))
        return top.to_dict(orient="records")
    return []


def _regime_frequency_change() -> dict:
    rl = loader.load_regime_labels().copy()
    _assert_finite(rl, ["date", "regime"], "regime_labels")
    rl["date"] = pd.to_datetime(rl["date"])
    rl["year"] = rl["date"].dt.year
    by_year     = rl.groupby(["year", "regime"]).size().unstack(fill_value=0)
    by_year_pct = by_year.div(by_year.sum(axis=1), axis=0)
    return {
        "counts": {int(y): {str(k): int(v)   for k, v in row.items()}
                   for y, row in by_year.to_dict(orient="index").items()},
        "pct":    {int(y): {str(k): float(v) for k, v in row.items()}
                   for y, row in by_year_pct.to_dict(orient="index").items()},
    }


def _state_distribution_shift() -> dict:
    panel = loader.load_panel().copy()
    _assert_finite(panel, ["date", "state_id"], "panel")
    panel["date"] = pd.to_datetime(panel["date"])
    median_date = panel["date"].median()
    pre  = panel[panel["date"] <  median_date]["state_id"].value_counts(normalize=True)
    post = panel[panel["date"] >= median_date]["state_id"].value_counts(normalize=True)
    union = pre.index.union(post.index)
    pre   = pre.reindex(union,  fill_value=0.0)
    post  = post.reindex(union, fill_value=0.0)
    shift = (post - pre).abs().sort_values(ascending=False).head(TOP_N)
    return {
        "split_date": str(median_date.date()),
        "top_shift_states": {int(k): float(v) for k, v in shift.to_dict().items()},
    }


def build() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    kl = _kl_topN()
    OUT_KL.write_text(json.dumps(kl, indent=2, default=str, allow_nan=False))

    drift = {
        "kl_topN":                  kl,
        "p_stay":                   _p_stay(),
        "transition_shift_matrix":  _transition_shift_matrix(),
        "regime_frequency_change":  _regime_frequency_change(),
        "state_distribution_shift": _state_distribution_shift(),
    }
    OUT_DRIFT.write_text(
        json.dumps(drift, indent=2, ensure_ascii=False,
                   default=str, allow_nan=False)
    )
    return drift


if __name__ == "__main__":
    d = build()
    print(f"diagnostics: kl_topN n={len(d['kl_topN'])}")
    print(f"  -> {OUT_KL}")
    print(f"  -> {OUT_DRIFT}")
