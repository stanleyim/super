"""
compute_state.py — STEP 1~4 daily full recompute

입력: data/raw/ohlcv/year=*.parquet
출력: data/cache/state_disc.parquet

backtest와 100% 동일 (drift = 0):
  - clean_panel
  - state_vector_raw (log return, sigma, volume)
  - state_vector_norm (rolling z-score, strict causal)
  - state_disc (rolling rank bin, vectorized)
"""
import os, sys, json, glob, time
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR  = os.path.join(ROOT, "data", "raw", "ohlcv")
CACHE_DIR = os.path.join(ROOT, "data", "cache")
CONFIG    = os.path.join(ROOT, "model", "deployment_config.json")

os.makedirs(CACHE_DIR, exist_ok=True)


def load_config():
    if not os.path.exists(CONFIG):
        return {"K":6, "WINDOW":252, "STD_FLOOR":1e-6, "Z_CLIP":5.0,
                "EPS":1e-8, "SIGMA_WINDOW":20, "VOLUME_WINDOW":20}
    with open(CONFIG) as f:
        cfg = json.load(f)
    cfg.setdefault("EPS", 1e-8)
    cfg.setdefault("SIGMA_WINDOW", 20)
    cfg.setdefault("VOLUME_WINDOW", 20)
    return cfg


def step1_clean_panel():
    files = sorted(glob.glob(f"{DATA_DIR}/year=*.parquet"))
    if not files:
        raise FileNotFoundError(f"OHLCV files not found: {DATA_DIR}")
    raw = pd.concat(
        [pd.read_parquet(f, columns=["date","code","close","volume"]) for f in files],
        ignore_index=True,
    )
    raw["date"] = pd.to_datetime(raw["date"])
    raw["code"] = raw["code"].astype(str).str.zfill(6)
    return (raw.drop_duplicates(["date","code"], keep="last")
               .dropna(subset=["close","volume"])
               .set_index(["date","code"]).sort_index()
               .astype("float64"))


def step2_state_vector(clean_panel, sigma_w=20, vol_w=20):
    out = []
    for code, g in clean_panel.groupby(level="code"):
        g = g.droplevel("code").sort_index()
        c, v = g["close"], g["volume"]
        p = np.log(c); r = p.diff()
        sv = pd.DataFrame({
            "p": p, "r": r,
            "sigma": r.rolling(sigma_w, min_periods=sigma_w).std(),
            "v": np.log1p(v),
            "l": v.rolling(vol_w, min_periods=vol_w).mean(),
        })
        sv["code"] = code
        out.append(sv)
    return (pd.concat(out).reset_index()
              .set_index(["date","code"]).sort_index().dropna())


def step3_normalize(svr, window, eps, std_floor, z_clip):
    NORM_COLS = ["r","sigma","v","l","p"]
    out = []
    for code in svr.index.get_level_values("code").unique():
        g = svr.xs(code, level="code").sort_index().copy()
        for col in NORM_COLS:
            s = g[col]
            mu = s.shift(1).rolling(window, min_periods=window).mean()
            sd = s.shift(1).rolling(window, min_periods=window).std().clip(lower=std_floor)
            g[f"z_{col}"] = ((s - mu) / (sd + eps)).clip(-z_clip, z_clip)
        g["code"] = code
        out.append(g)
    df = (pd.concat(out).reset_index()
            .set_index(["date","code"]).sort_index())
    return df.dropna(subset=[f"z_{c}" for c in NORM_COLS])


def rolling_rank_bin_fast(arr, window, K):
    n = len(arr)
    out = np.full(n, np.nan, dtype=np.float64)
    if n <= window:
        return out
    past = sliding_window_view(arr, window)[:-1]
    targets = arr[window:]
    cmp = past < targets[:, None]
    valid = ~np.isnan(targets) & ~np.isnan(past).any(axis=1)
    rank_pct = np.where(valid, cmp.sum(axis=1)/window, np.nan)
    out[window:] = np.clip(np.floor(rank_pct * K), 0, K-1)
    return out


def step4_discretize(svn, window, K):
    BIN_COLS = ["z_r","z_sigma","z_v","z_l","z_p"]
    WEIGHTS  = [K**i for i in range(len(BIN_COLS))]
    out = []
    for code in svn.index.get_level_values("code").unique():
        g = svn.xs(code, level="code").sort_index().copy()
        for col in BIN_COLS:
            g[f"{col}_bin"] = rolling_rank_bin_fast(g[col].values, window, K)
        bin_cols = [f"{c}_bin" for c in BIN_COLS]
        g["state_id"] = sum(g[bin_cols[j]] * WEIGHTS[j] for j in range(len(BIN_COLS)))
        g["code"] = code
        out.append(g)
    df = (pd.concat(out).reset_index()
            .set_index(["date","code"]).sort_index())
    df = df.dropna(subset=["state_id"] + [f"{c}_bin" for c in BIN_COLS])
    df["state_id"] = df["state_id"].astype(int)
    for c in BIN_COLS:
        df[f"{c}_bin"] = df[f"{c}_bin"].astype(int)
    return df


def main():
    cfg = load_config()
    print(f"=== compute_state.py (full recompute) ===")
    print(f"   K={cfg['K']} WINDOW={cfg['WINDOW']} STD_FLOOR={cfg['STD_FLOOR']} Z_CLIP={cfg['Z_CLIP']}")

    t = time.time()
    print("[1/4] clean_panel ...", end=" ", flush=True)
    cp = step1_clean_panel()
    print(f"{cp.shape} ({time.time()-t:.1f}s)")

    t = time.time()
    print("[2/4] state_vector_raw ...", end=" ", flush=True)
    svr = step2_state_vector(cp, cfg["SIGMA_WINDOW"], cfg["VOLUME_WINDOW"])
    print(f"{svr.shape} ({time.time()-t:.1f}s)")

    t = time.time()
    print("[3/4] state_vector_norm ...", end=" ", flush=True)
    svn = step3_normalize(svr, cfg["WINDOW"], cfg["EPS"],
                          cfg["STD_FLOOR"], cfg["Z_CLIP"])
    print(f"{svn.shape} ({time.time()-t:.1f}s)")

    t = time.time()
    print("[4/4] state_disc ...", end=" ", flush=True)
    sd = step4_discretize(svn, cfg["WINDOW"], cfg["K"])
    print(f"{sd.shape} ({time.time()-t:.1f}s)")

    out_path = os.path.join(CACHE_DIR, "state_disc.parquet")
    sd.reset_index().to_parquet(out_path, index=False)
    last_date = sd.index.get_level_values("date").max()
    n_codes = sd.index.get_level_values("code").nunique()
    print(f"\n[OK] saved -> {out_path}")
    print(f"     last_date: {last_date.date()}, codes: {n_codes}, "
          f"size: {os.path.getsize(out_path)/1e6:.1f}MB")


if __name__ == "__main__":
    main()
