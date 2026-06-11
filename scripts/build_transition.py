"""
build_transition.py — MSM Regime + Transition Matrix (STEP 5~6)
"""
import os, sys, glob, argparse, json
import numpy as np
import pandas as pd

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SV_DIR   = os.path.join(ROOT, "data", "processed", "state_vector")
OUT_DIR  = os.path.join(ROOT, "data", "processed", "transition")
PANEL_DIR = os.path.join(OUT_DIR, "panel_with_regime")

K, N_STATES = 6, 6**4
REGIMES = ["SHOCK", "TREND", "RANGE", "TRANSITION"]
LOG_EPS = 1e-12


def load_state_vector(fy=None, ty=None):
    files = sorted(glob.glob(f"{SV_DIR}/year=*.parquet"))
    if not files: raise FileNotFoundError(SV_DIR)
    parts = []
    for f in files:
        y = int(os.path.basename(f).replace("year=","").replace(".parquet",""))
        if fy is not None and y < fy: continue
        if ty is not None and y > ty: continue
        parts.append(pd.read_parquet(f, columns=["date","code","r","z_r","state_id"]))
    df = pd.concat(parts, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["code","date"]).reset_index(drop=True)
    df["state_id"] = df["state_id"].astype(int)
    return df


def add_forward_return(df):
    g = df.groupby("code", sort=False)
    df["next_r"] = g["r"].shift(-1)
    df["next_r_z"] = g["z_r"].shift(-1)
    df["next_state"] = g["state_id"].shift(-1)
    return df


def compute_state_stats(df):
    valid = df.dropna(subset=["next_r","next_r_z","next_state"]).copy()
    valid["next_state"] = valid["next_state"].astype(int)
    g = valid.groupby("state_id")
    stats = g.agg(visits=("next_r","size"), mu_r_raw=("next_r","mean"),
                  sigma_r_raw=("next_r","std"), mu_r=("next_r_z","mean"),
                  sigma_r=("next_r_z","std")).reset_index()
    stay = (valid["next_state"] == valid["state_id"]).astype(int)
    p_stay = valid.assign(stay=stay).groupby("state_id")["stay"].mean().rename("p_stay").reset_index()
    stats = stats.merge(p_stay, on="state_id", how="left")
    all_s = pd.DataFrame({"state_id": np.arange(N_STATES)})
    stats = all_s.merge(stats, on="state_id", how="left")
    stats["visits"] = stats["visits"].fillna(0).astype(int)
    sid = stats["state_id"].values
    stats["bin_r"] = sid % K
    stats["bin_sigma"] = (sid // K) % K
    stats["bin_v"] = (sid // (K**2)) % K
    stats["bin_flow"] = (sid // (K**3)) % K
    return stats, valid


def compute_transition_global(valid):
    s = valid["state_id"].values
    s2 = valid["next_state"].values
    counts = np.zeros((N_STATES, N_STATES), dtype=np.int64)
    np.add.at(counts, (s, s2), 1)
    rs = counts.sum(axis=1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        P = np.where(rs > 0, counts/rs, 0.0).astype(np.float32)
    return P


def compute_entropy(P):
    with np.errstate(divide="ignore", invalid="ignore"):
        logP = np.where(P > 0, np.log(P + LOG_EPS), 0.0)
    return -(P * logP).sum(axis=1).astype(np.float32)


def classify_regime(state_table):
    df = state_table.copy()
    mask = df["visits"] > 0
    sub = df[mask]
    abs_mu = sub["mu_r"].abs()
    q70_s = sub["sigma_r"].quantile(0.70); q30_s = sub["sigma_r"].quantile(0.30)
    med_s = sub["sigma_r"].median()
    q70_mu = abs_mu.quantile(0.70); med_mu = abs_mu.median()
    med_e = sub["entropy"].median()
    print(f"  σ Q30={q30_s:.4f} med={med_s:.4f} Q70={q70_s:.4f} | |μ| med={med_mu:.4f} Q70={q70_mu:.4f} | H med={med_e:.4f}")
    regime = pd.Series("TRANSITION", index=df.index, dtype=object)
    abs_mu_full = df["mu_r"].abs()
    shock = mask & (df["sigma_r"] >= q70_s) & (df["entropy"] >= med_e)
    regime[shock] = "SHOCK"
    trend = mask & ~shock & (abs_mu_full >= q70_mu) & (df["sigma_r"] >= med_s)
    regime[trend] = "TREND"
    rng = mask & ~shock & ~trend & (df["sigma_r"] <= q30_s) & (abs_mu_full < med_mu)
    regime[rng] = "RANGE"
    regime[~mask] = "UNKNOWN"
    df["regime"] = regime
    return df, {"q70_sigma": float(q70_s), "q30_sigma": float(q30_s),
                "med_sigma": float(med_s), "q70_mu_abs": float(q70_mu),
                "med_mu_abs": float(med_mu), "med_entropy": float(med_e)}


def compute_transition_by_regime(valid, state_table):
    rm = state_table.set_index("state_id")["regime"].to_dict()
    v = valid.copy()
    v["regime_s"] = v["state_id"].map(rm)
    P_dict, c_dict = {}, {}
    for r in REGIMES:
        sub = v[v["regime_s"] == r]
        counts = np.zeros((N_STATES, N_STATES), dtype=np.int64)
        if len(sub) > 0:
            np.add.at(counts, (sub["state_id"].values, sub["next_state"].astype(int).values), 1)
        rs = counts.sum(axis=1, keepdims=True)
        with np.errstate(divide="ignore", invalid="ignore"):
            P = np.where(rs > 0, counts/rs, 0.0).astype(np.float32)
        P_dict[r] = P
        c_dict[r] = int(counts.sum())
    return P_dict, c_dict


def save_outputs(state_table, P_global, P_by_regime, valid, dry_run=False):
    os.makedirs(OUT_DIR, exist_ok=True)
    cols = ["state_id","bin_r","bin_sigma","bin_v","bin_flow","visits",
            "mu_r","sigma_r","mu_r_raw","sigma_r_raw","p_stay","entropy","regime"]
    if not dry_run:
        state_table[cols].to_parquet(f"{OUT_DIR}/state_table.parquet", index=False)
        np.savez_compressed(f"{OUT_DIR}/transition_matrix.npz",
            P_global=P_global, state_ids=np.arange(N_STATES, dtype=np.int32),
            **{f"P_{r}": P_by_regime[r] for r in REGIMES})
        s_idx, s2_idx = np.nonzero(P_global)
        pd.DataFrame({"s": s_idx.astype(np.int32), "s_next": s2_idx.astype(np.int32),
                      "p": P_global[s_idx, s2_idx].astype(np.float32)}).to_parquet(
            f"{OUT_DIR}/transition_long.parquet", index=False)
        os.makedirs(PANEL_DIR, exist_ok=True)
        rm = state_table.set_index("state_id")["regime"].to_dict()
        panel = valid[["date","code","state_id","next_r","next_r_z"]].copy()
        panel["regime"] = panel["state_id"].map(rm)
        panel["next_state"] = valid["next_state"].astype(int).values
        panel["__year"] = panel["date"].dt.year
        for year, grp in panel.groupby("__year"):
            out = grp.drop(columns=["__year"]).sort_values(["date","code"]).reset_index(drop=True)
            out.to_parquet(f"{PANEL_DIR}/year={year}.parquet", index=False)
    print(f"  saved (dry_run={dry_run})")


def verify():
    st_path = f"{OUT_DIR}/state_table.parquet"
    if not os.path.exists(st_path): print("[verify] none"); return False
    st = pd.read_parquet(st_path)
    npz = np.load(f"{OUT_DIR}/transition_matrix.npz")
    P = npz["P_global"]
    rs = P.sum(axis=1)
    bad = (rs > 0) & (np.abs(rs - 1.0) > 1e-4)
    if bad.any(): print(f"[verify] ❌ row sums"); return False
    print(f"[verify] ✅ states={len(st)} regimes={st['regime'].value_counts().to_dict()}")
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--from-year", type=int); p.add_argument("--to-year", type=int)
    p.add_argument("--dry-run", action="store_true"); p.add_argument("--verify", action="store_true")
    args = p.parse_args()
    if args.verify: sys.exit(0 if verify() else 1)
    print("[load]"); df = load_state_vector(args.from_year, args.to_year)
    print(f"  {len(df):,} rows | {df['code'].nunique()} codes")
    df = add_forward_return(df)
    state_table, valid = compute_state_stats(df)
    print(f"[stats] populated: {(state_table['visits']>0).sum()}/{N_STATES}")
    P_global = compute_transition_global(valid)
    state_table["entropy"] = compute_entropy(P_global)
    state_table, thr = classify_regime(state_table)
    P_by_regime, _ = compute_transition_by_regime(valid, state_table)
    for r in REGIMES:
        n = (state_table["regime"]==r).sum()
        print(f"  {r:10s}: {n:4d} states")
    save_outputs(state_table, P_global, P_by_regime, valid, dry_run=args.dry_run)
    if not args.dry_run:
        with open(f"{OUT_DIR}/regime_thresholds.json","w") as f: json.dump(thr, f, indent=2)
    print(f"\n✅" + (" (DRY)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
