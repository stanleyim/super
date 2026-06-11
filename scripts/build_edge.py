"""
build_edge.py — MSM Edge Field + Tradeable Region (STEP 7~8)
LOCKED: E=both, MIN_VISITS=100, T=2.0, regime∈{TREND,RANGE}
"""
import os, sys, argparse
import numpy as np
import pandas as pd

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TR_DIR   = os.path.join(ROOT, "data", "processed", "transition")
OUT_DIR  = os.path.join(ROOT, "data", "processed", "edge")

MIN_VISITS = 100
T_THRESHOLD = 2.0
TRADEABLE_REG = {"TREND", "RANGE"}


def compute_edge(state_table):
    df = state_table.copy()
    df["E_raw"] = df["mu_r_raw"]
    df["E_z"] = df["mu_r"]
    df["E_sharpe_raw"] = df["mu_r_raw"] / df["sigma_r_raw"].replace(0, np.nan)
    df["E_sharpe_z"] = df["mu_r"] / df["sigma_r"].replace(0, np.nan)
    df["E_stay_raw"] = df["mu_r_raw"] * df["p_stay"]
    df["E_stay_z"] = df["mu_r"] * df["p_stay"]
    se = df["sigma_r_raw"] / np.sqrt(df["visits"].replace(0, np.nan))
    df["t_stat"] = df["mu_r_raw"] / se.replace(0, np.nan)
    return df


def extract_tradeable(edge):
    mask = ((edge["E_raw"] > 0) & (edge["visits"] >= MIN_VISITS) &
            (edge["t_stat"] >= T_THRESHOLD) & (edge["regime"].isin(TRADEABLE_REG)))
    return edge[mask].copy()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    st_path = f"{TR_DIR}/state_table.parquet"
    if not os.path.exists(st_path):
        print(f"❌ {st_path} not found"); sys.exit(1)
    st = pd.read_parquet(st_path)
    print(f"[load] states={len(st)} populated={(st['visits']>0).sum()}")
    edge = compute_edge(st)
    tradeable = extract_tradeable(edge)
    print(f"\n[summary]")
    print(f"  E>0: {(edge['E_raw']>0).sum()} | visits>={MIN_VISITS}: {(edge['visits']>=MIN_VISITS).sum()}")
    print(f"  t>={T_THRESHOLD}: {(edge['t_stat']>=T_THRESHOLD).sum()} | regime: {edge['regime'].isin(TRADEABLE_REG).sum()}")
    print(f"  TRADEABLE: {len(tradeable)}")
    if len(tradeable) > 0:
        print(f"  regime: {tradeable['regime'].value_counts().to_dict()}")
        print(f"  E_raw: [{tradeable['E_raw'].min():.6f}, {tradeable['E_raw'].max():.6f}]")
        print(f"  t_stat: [{tradeable['t_stat'].min():.2f}, {tradeable['t_stat'].max():.2f}]")
    os.makedirs(OUT_DIR, exist_ok=True)
    if not args.dry_run:
        edge.to_parquet(f"{OUT_DIR}/edge_table.parquet", index=False)
        tradeable.to_parquet(f"{OUT_DIR}/tradeable.parquet", index=False)
    print(f"\n✅" + (" (DRY)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
