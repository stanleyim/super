"""
build_state_vector.py — MSM State Vector (STEP 2~4)
LOCKED: K=6, W_sigma=20, W_z=252, features=[z_r,z_sigma,z_v,z_flow]
"""
import os, sys, glob, argparse
import numpy as np
import pandas as pd

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR  = os.path.join(ROOT, "data", "raw", "ohlcv")
OUT_DIR  = os.path.join(ROOT, "data", "processed", "state_vector")

W_SIGMA, W_LIQ, W_Z, K = 20, 20, 252, 6
OUT_COLS = ["date","code","close","p","r","sigma","v","l","flow",
            "z_r","z_sigma","z_v","z_flow",
            "bin_r","bin_sigma","bin_v","bin_flow","state_id"]


def load_panel(fy=None, ty=None):
    files = sorted(glob.glob(f"{RAW_DIR}/year=*.parquet"))
    if not files: raise FileNotFoundError(RAW_DIR)
    parts = []
    for f in files:
        y = int(os.path.basename(f).replace("year=","").replace(".parquet",""))
        if fy is not None and y < fy: continue
        if ty is not None and y > ty: continue
        parts.append(pd.read_parquet(f, columns=["date","code","close","volume","trade_value"]))
    panel = pd.concat(parts, ignore_index=True)
    panel["date"] = pd.to_datetime(panel["date"])
    return panel.sort_values(["code","date"]).reset_index(drop=True)


def compute_raw_state(panel):
    df = panel.copy()
    df["p"] = np.log(df["close"])
    df["v"] = np.log1p(df["volume"])
    log_tv = np.log1p(df["trade_value"])
    g = df.groupby("code", sort=False)
    df["r"] = g["p"].diff()
    df["sigma"] = g["r"].rolling(W_SIGMA, min_periods=W_SIGMA).std().reset_index(level=0, drop=True)
    df["l"] = g["v"].rolling(W_LIQ, min_periods=W_LIQ).mean().reset_index(level=0, drop=True)
    df["flow"] = log_tv.groupby(df["code"], sort=False).diff()
    return df


def _zscore(s, code, W):
    mu = s.groupby(code, sort=False).transform(lambda x: x.shift(1).rolling(W, min_periods=W).mean())
    sd = s.groupby(code, sort=False).transform(lambda x: x.shift(1).rolling(W, min_periods=W).std())
    return (s - mu) / sd.replace(0, np.nan)


def apply_zscore(df, W=W_Z):
    c = df["code"]
    for col in ["r","sigma","v","flow"]:
        df[f"z_{col}"] = _zscore(df[col], c, W)
    return df


def _qbin(s, K):
    try: return pd.qcut(s, K, labels=False, duplicates="drop")
    except ValueError: return pd.Series(np.nan, index=s.index)


def apply_discretization(df, K=K):
    g = df.groupby("code", sort=False)
    for col in ["r","sigma","v","flow"]:
        df[f"bin_{col}"] = g[f"z_{col}"].transform(lambda s: _qbin(s, K))
    bins = df[["bin_r","bin_sigma","bin_v","bin_flow"]]
    valid = bins.notna().all(axis=1)
    sid = (bins["bin_r"] + bins["bin_sigma"]*K + bins["bin_v"]*(K**2) + bins["bin_flow"]*(K**3))
    sid[~valid] = np.nan
    df["state_id"] = sid
    for c in ["bin_r","bin_sigma","bin_v","bin_flow"]: df[c] = df[c].astype("Int64")
    df["state_id"] = df["state_id"].astype("Int64")
    return df


def save_state_vector(df, dry_run=False):
    n0 = len(df)
    df = df[df["state_id"].notna()].copy()
    print(f"  dropped {n0-len(df):,} warmup, {len(df):,} remain ({len(df)/max(n0,1)*100:.1f}%)")
    df = df[OUT_COLS]
    df["__year"] = df["date"].dt.year
    os.makedirs(OUT_DIR, exist_ok=True)
    saved = 0
    for year, grp in df.groupby("__year"):
        out = grp.drop(columns=["__year"]).sort_values(["date","code"]).reset_index(drop=True)
        path = f"{OUT_DIR}/year={year}.parquet"
        if not dry_run: out.to_parquet(path, index=False)
        saved += len(out)
        print(f"  year={year}: {len(out):,}")
    return saved


def verify():
    files = sorted(glob.glob(f"{OUT_DIR}/year=*.parquet"))
    if not files: print("[verify] none"); return False
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    sid = df["state_id"]
    if sid.min() < 0 or sid.max() >= K**4:
        print(f"[verify] ❌ state_id range"); return False
    print(f"[verify] ✅ rows={len(df):,} unique_states={sid.nunique()}/{K**4}")
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--from-year", type=int); p.add_argument("--to-year", type=int)
    p.add_argument("--dry-run", action="store_true"); p.add_argument("--verify", action="store_true")
    args = p.parse_args()
    if args.verify: sys.exit(0 if verify() else 1)
    panel = load_panel(args.from_year, args.to_year)
    print(f"[load] {len(panel):,} rows | {panel['code'].nunique()} codes")
    df = compute_raw_state(panel)
    df = apply_zscore(df)
    df = apply_discretization(df)
    n = save_state_vector(df, dry_run=args.dry_run)
    print(f"\n✅ {n:,} rows" + (" (DRY)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
