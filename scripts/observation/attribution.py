"""STAGE 2 attribution - PnL decomposition.

LOCKED: D1 = both (ret_net + ret_gross), D2 = split.
G2:     finite-value guards on loader output + json allow_nan=False.

Output schema (attribution_summary.json):
  total_pnl, ret_net, ret_gross, pnl_by_regime, pnl_by_state,
  pnl_by_asset, top_contributors, worst_contributors
"""
import json
from pathlib import Path
from typing import Dict, Iterable

import numpy as np
import pandas as pd

from scripts.observation import loader

OUT_DIR     = Path("data/processed/observation")
OUT_PARQUET = OUT_DIR / "attribution.parquet"
OUT_SUMMARY = OUT_DIR / "attribution_summary.json"

TOP_N = 20


def _assert_finite(df: pd.DataFrame, cols: Iterable[str], name: str) -> None:
    """Hard-fail on NaN or +/-inf in numeric columns; NaN-only check for others."""
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


def _stats(s: pd.Series) -> Dict[str, float]:
    return {
        "n":    int(s.shape[0]),
        "sum":  float(s.sum()),
        "mean": float(s.mean()) if len(s) else 0.0,
        "std":  float(s.std(ddof=1)) if len(s) > 1 else 0.0,
    }


def build() -> pd.DataFrame:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    trades = loader.load_trades()
    _assert_finite(
        trades,
        ["ret_net", "ret_gross", "state_id", "regime", "code"],
        "trades",
    )

    state_class = loader.load_state_class()
    sc_df = pd.DataFrame(
        [(int(k), v) for k, v in state_class.items()],
        columns=["state_id", "class"],
    )
    _assert_finite(sc_df, ["state_id", "class"], "state_class")

    df = trades.merge(sc_df, on="state_id", how="left")
    df["class"] = df["class"].fillna("UNCLASSIFIED")
    df.to_parquet(OUT_PARQUET, index=False)

    summary = {
        "total_pnl": {
            "ret_net":   float(df["ret_net"].sum()),
            "ret_gross": float(df["ret_gross"].sum()),
        },
        "ret_net":   _stats(df["ret_net"]),
        "ret_gross": _stats(df["ret_gross"]),
        "pnl_by_regime": {
            "ret_net":   df.groupby("regime")["ret_net"].sum().to_dict(),
            "ret_gross": df.groupby("regime")["ret_gross"].sum().to_dict(),
        },
        "pnl_by_state": {
            "ret_net":   df.groupby("state_id")["ret_net"].sum()
                          .sort_values(ascending=False).head(TOP_N).to_dict(),
            "ret_gross": df.groupby("state_id")["ret_gross"].sum()
                          .sort_values(ascending=False).head(TOP_N).to_dict(),
        },
        "pnl_by_asset": {
            "ret_net":   df.groupby("code")["ret_net"].sum()
                          .sort_values(ascending=False).head(TOP_N).to_dict(),
            "ret_gross": df.groupby("code")["ret_gross"].sum()
                          .sort_values(ascending=False).head(TOP_N).to_dict(),
        },
        "top_contributors": (
            df.groupby(["code", "state_id"])
              .agg(ret_net_sum=("ret_net", "sum"),
                   ret_gross_sum=("ret_gross", "sum"),
                   n=("ret_net", "size"))
              .sort_values("ret_net_sum", ascending=False)
              .head(TOP_N).reset_index().to_dict(orient="records")
        ),
        "worst_contributors": (
            df.groupby(["code", "state_id"])
              .agg(ret_net_sum=("ret_net", "sum"),
                   ret_gross_sum=("ret_gross", "sum"),
                   n=("ret_net", "size"))
              .sort_values("ret_net_sum", ascending=True)
              .head(TOP_N).reset_index().to_dict(orient="records")
        ),
    }
    # G2 output-side guard: allow_nan=False raises on any NaN/Inf during dump
    OUT_SUMMARY.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False,
                   default=str, allow_nan=False)
    )
    return df


if __name__ == "__main__":
    df = build()
    print(f"attribution: rows={len(df):,}")
    print(f"  -> {OUT_PARQUET}")
    print(f"  -> {OUT_SUMMARY}")
