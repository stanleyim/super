"""
build_regime.py — STEP 2 REGIME CLASSIFICATION (LOCKED SPEC, HANDOFF_v3 §6)

PIPELINE (§6.1):
  panel.parquet
    → X_cont = (p, v, flow, sigma, l)                       [§5.2 ORDERING INVARIANT]
    → zscore(per-asset, W_norm=252, shift(1))               [TIER 1 S1]
    → valid_mask: strict all-finite over 5 channels         [TIER 2 S7]
    → k-means(K=8, k-means++/42, n_init=20, max=300, tol=1e-4, L2, lloyd)  [TIER 3]
    → CategoricalHMM(8, n_iter=200, tol=1e-3, EM, pooled, split-on-invalid) [TIER 3]
    → π ← stationary(T_HMM) post-fit (fallback uniform)     [TIER 3 B7-a]
    → label_map (bin_r, bin_sigma only; bin_v/bin_flow 미사용 — O2(a))
  OUTPUT:
    Z_t ∈ {-1, 0..7}                R_t ∈ {NaN, TREND, RANGE, SHOCK, TRANSITION}
    T_HMM ∈ ℝ^{8×8} (diagnostic)    label_map dict
"""
import os, sys, glob, json, argparse
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from hmmlearn.hmm import CategoricalHMM

# ============ PATHS ============
ROOT     = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SV_DIR   = os.path.join(ROOT, "data", "processed", "state_vector")
OUT_DIR  = os.path.join(ROOT, "data", "processed", "regime")
LOG_DIR  = os.path.join(ROOT, "reports", "run_logs")

# ============ CONSTANTS (LOCKED) ============
W_NORM   = 252
K_REGIME = 8
K_BIN    = 6
SEED     = 42
FEATURES = ["p", "v", "flow", "sigma", "l"]   # §5.2 ORDERING INVARIANT
Z_COLS   = [f"z_{f}" for f in FEATURES]

KM_PARAMS  = dict(n_clusters=K_REGIME, init="k-means++", n_init=20,
                  max_iter=300, tol=1e-4, algorithm="lloyd", random_state=SEED)
HMM_PARAMS = dict(n_components=K_REGIME, n_iter=200, tol=1e-3, random_state=SEED)

# §6.2 dominance (bin_r, bin_sigma ONLY)
TREND_BIN_R     = {0, 1, 4, 5}
RANGE_BIN_R     = {2, 3}
LOW_BIN_SIGMA   = {0, 1}
SHOCK_BIN_SIGMA = {4, 5}
TIE_PRIORITY    = ["SHOCK", "TRANSITION", "TREND", "RANGE"]


# ============ LOAD (§5.1 projection) ============
def load_panel():
    p = os.path.join(SV_DIR, "panel.parquet")
    if os.path.exists(p):
        df = pd.read_parquet(p)
    else:
        files = sorted(glob.glob(os.path.join(SV_DIR, "year=*.parquet")))
        if not files:
            raise FileNotFoundError(f"no state_vector parquet in {SV_DIR}")
        df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    keep = ["date", "code", "state_id", "p", "v", "flow", "sigma", "l"]
    df = df[keep].copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["code", "date"]).reset_index(drop=True)
    return df


# ============ S1: zscore (per-asset rolling, shift(1)) ============
def _zscore(s, code, W):
    mu = s.groupby(code, sort=False).transform(
        lambda x: x.shift(1).rolling(W, min_periods=W).mean())
    sd = s.groupby(code, sort=False).transform(
        lambda x: x.shift(1).rolling(W, min_periods=W).std())
    return (s - mu) / sd.replace(0, np.nan)


def normalize(df, W=W_NORM):
    for f in FEATURES:
        df[f"z_{f}"] = _zscore(df[f], df["code"], W)
    return df


# ============ S7: valid_mask (strict all-finite, no fill/interp) ============
def build_valid_mask(df):
    df["valid"] = np.isfinite(df[Z_COLS].to_numpy()).all(axis=1)
    return df


# ============ TIER 3 B1·B3·B5: k-means ============
def run_kmeans(df):
    X = df.loc[df["valid"], Z_COLS].to_numpy()
    km = KMeans(**KM_PARAMS)
    C = km.fit_predict(X)
    df["C_t"] = -1
    df.loc[df["valid"], "C_t"] = C
    return df, km


# ============ S7-a: split-on-invalid → per-asset sub-sequences ============
def build_sequences(df):
    seq_list, lengths, idx_map = [], [], []
    for code, sub in df.groupby("code", sort=False):
        sub = sub.sort_values("date")
        ci = sub["C_t"].to_numpy()
        vi = (ci != -1)
        if not vi.any():
            continue
        diff = np.diff(vi.astype(np.int8))
        starts = np.where(diff ==  1)[0] + 1
        ends   = np.where(diff == -1)[0] + 1
        if vi[0]:  starts = np.concatenate(([0],   starts))
        if vi[-1]: ends   = np.concatenate((ends, [len(vi)]))
        for s, e in zip(starts, ends):
            if e > s:
                seq_list.append(ci[s:e])
                lengths.append(int(e - s))
                idx_map.append(sub.index[s:e].to_numpy())
    X_seq = np.concatenate(seq_list).reshape(-1, 1).astype(int)
    return X_seq, lengths, idx_map


# ============ M1 + B6 + B7-a: CategoricalHMM pooled fit ============
def _stationary_or_uniform(T):
    K = T.shape[0]
    eigvals, eigvecs = np.linalg.eig(T.T)
    # reducibility/periodicity: more than one unit-modulus eigenvalue
    unit_count = int((np.abs(np.abs(eigvals) - 1.0) < 1e-6).sum())
    if unit_count > 1:
        return np.full(K, 1.0 / K), True, unit_count
    idx = int(np.argmin(np.abs(eigvals - 1.0)))
    pi  = np.real(eigvecs[:, idx])
    s   = pi.sum()
    if abs(s) < 1e-12:
        return np.full(K, 1.0 / K), True, unit_count
    pi = pi / s
    if (pi < -1e-9).any():
        return np.full(K, 1.0 / K), True, unit_count
    pi = np.clip(pi, 0.0, None)
    pi = pi / pi.sum()
    return pi, False, unit_count


def fit_hmm(X_seq, lengths):
    hmm = CategoricalHMM(
        **HMM_PARAMS,
        init_params="te",   # 's' 제외 → manual uniform startprob 보존
        params="ste",       # EM 동안 모두 업데이트
    )
    hmm.startprob_ = np.full(K_REGIME, 1.0 / K_REGIME)
    hmm.n_features = K_REGIME
    hmm.fit(X_seq, lengths=lengths)
    T_HMM = hmm.transmat_.copy()
    pi_final, fallback, unit_count = _stationary_or_uniform(T_HMM)
    hmm.startprob_ = pi_final
    return hmm, T_HMM, pi_final, fallback, unit_count


# ============ predict Z_t per sub-sequence, scatter back ============
def predict_Z(hmm, X_seq, lengths, idx_map, df):
    df["Z_t"] = -1
    offset = 0
    for L, idx in zip(lengths, idx_map):
        seg = X_seq[offset:offset + L]
        Z_seg = hmm.predict(seg, lengths=[L])
        df.loc[idx, "Z_t"] = Z_seg
        offset += L
    return df


# ============ S5 + label_map (bin_r, bin_sigma only) ============
def decode_bin_r_sigma(sid_arr):
    sid = np.asarray(sid_arr, dtype=np.int64)
    bin_r     =  sid           % K_BIN
    bin_sigma = (sid // K_BIN) % K_BIN
    return bin_r, bin_sigma


def compute_label_map(df):
    sub = df[df["Z_t"] != -1].copy()
    bin_r, bin_sigma = decode_bin_r_sigma(sub["state_id"].to_numpy())
    is_trend = np.isin(bin_r, list(TREND_BIN_R)) & np.isin(bin_sigma, list(LOW_BIN_SIGMA))
    is_range = np.isin(bin_r, list(RANGE_BIN_R)) & np.isin(bin_sigma, list(LOW_BIN_SIGMA))
    is_shock = np.isin(bin_sigma, list(SHOCK_BIN_SIGMA))
    sub["_trend"], sub["_range"], sub["_shock"] = is_trend, is_range, is_shock

    label_map, scores_log = {}, {}
    for z in range(K_REGIME):
        s = sub[sub["Z_t"] == z]
        n = len(s)
        if n == 0:
            label_map[z] = "TRANSITION"
            scores_log[z] = dict(n=0, shock=0.0, transition=1.0, trend=0.0, range=0.0)
            continue
        ts = float(s["_trend"].mean())
        rs = float(s["_range"].mean())
        ss = float(s["_shock"].mean())
        xs = 1.0 - (ts + rs + ss)
        scores = {"SHOCK": ss, "TRANSITION": xs, "TREND": ts, "RANGE": rs}
        m = max(scores.values())
        for label in TIE_PRIORITY:                  # tie-break: shock > transition > trend > range
            if scores[label] == m:
                label_map[z] = label
                break
        scores_log[z] = dict(n=int(n), shock=ss, transition=xs, trend=ts, range=rs)
    return label_map, scores_log


def apply_label_map(df, label_map):
    df["R_t"] = pd.NA
    m = df["Z_t"] != -1
    df.loc[m, "R_t"] = df.loc[m, "Z_t"].map(label_map)
    return df


# ============ SAVE ============
def save_outputs(df, T_HMM, pi_final, label_map, scores_log, fallback, unit_count):
    os.makedirs(OUT_DIR, exist_ok=True)
    out_cols = ["date", "code", "state_id", "Z_t", "R_t"]
    df[out_cols].to_parquet(os.path.join(OUT_DIR, "regime.parquet"), index=False)
    np.save(os.path.join(OUT_DIR, "T_HMM.npy"), T_HMM)
    meta = {
        "label_map": {int(k): v for k, v in label_map.items()},
        "scores":    {int(k): v for k, v in scores_log.items()},
        "stationary": {
            "fallback_uniform": bool(fallback),
            "unit_modulus_eigs": int(unit_count),
            "pi": pi_final.tolist(),
        },
        "params": {
            "W_NORM": W_NORM, "K_REGIME": K_REGIME, "K_BIN": K_BIN, "SEED": SEED,
            "FEATURES": FEATURES, "KM": KM_PARAMS, "HMM": HMM_PARAMS,
        },
    }
    with open(os.path.join(OUT_DIR, "label_map.json"), "w") as f:
        json.dump(meta, f, indent=2, default=str)


# ============ VERIFY (§PHASE 4) ============
def verify(df, T_HMM, label_map):
    print("\n=== VERIFY ===")
    print(f"rows           : {len(df):,}")
    print(f"codes          : {df['code'].nunique()}")
    print(f"dates          : {df['date'].nunique()}")
    inv = (df["Z_t"] == -1)
    val = ~inv
    print(f"invalid (-1)   : {inv.sum():,}  ({inv.mean()*100:.2f}%)")
    print(f"valid          : {val.sum():,}  ({val.mean()*100:.2f}%)")
    if val.any():
        zmin, zmax = df.loc[val, "Z_t"].min(), df.loc[val, "Z_t"].max()
        print(f"Z_t range      : [{zmin}, {zmax}]")
        print(f"Z_t distrib    :\n{df.loc[val, 'Z_t'].value_counts().sort_index().to_string()}")
        print(f"R_t distrib    :\n{df.loc[val, 'R_t'].value_counts().to_string()}")
    print(f"T_HMM row sums : {T_HMM.sum(axis=1).round(6)}")
    print(f"label_map      : {label_map}")
    # sentinel consistency
    rnan = df["R_t"].isna()
    assert (inv == rnan).all(), "ABORT: Z_t=-1 ↔ R_t=NaN 불일치"
    print("✅ Z_t=-1 ↔ R_t=NaN consistent")


# ============ MAIN ============
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print("[1/8] load_panel")
    df = load_panel()
    print(f"      rows={len(df):,}  codes={df['code'].nunique()}  dates={df['date'].nunique()}")

    print(f"[2/8] normalize (W={W_NORM}, per-asset, shift(1))")
    df = normalize(df)

    print("[3/8] valid_mask (strict all-finite, 5ch)")
    df = build_valid_mask(df)
    print(f"      valid rows : {df['valid'].sum():,} / {len(df):,}  ({df['valid'].mean()*100:.2f}%)")

    print(f"[4/8] k-means (K={K_REGIME}, seed={SEED}, n_init=20)")
    df, km = run_kmeans(df)
    cluster_counts = df.loc[df["valid"], "C_t"].value_counts().sort_index()
    print(f"      C_t counts :\n{cluster_counts.to_string()}")

    print("[5/8] sequences (split-on-invalid, per-asset)")
    X_seq, lengths, idx_map = build_sequences(df)
    print(f"      sequences  : {len(lengths):,}   obs: {len(X_seq):,}   "
          f"min={min(lengths)}  max={max(lengths)}  mean={np.mean(lengths):.1f}")

    print(f"[6/8] CategoricalHMM (K={K_REGIME}, n_iter=200, EM, pooled)")
    hmm, T_HMM, pi_final, fallback, unit_count = fit_hmm(X_seq, lengths)
    print(f"      unit-modulus eigs : {unit_count}")
    print(f"      stationary π      : {pi_final.round(4)}")
    print(f"      fallback uniform  : {fallback}")

    print("[7/8] predict Z_t")
    df = predict_Z(hmm, X_seq, lengths, idx_map, df)

    print("[8/8] label_map + R_t")
    label_map, scores_log = compute_label_map(df)
    df = apply_label_map(df, label_map)

    verify(df, T_HMM, label_map)

    if not args.dry_run:
        save_outputs(df, T_HMM, pi_final, label_map, scores_log, fallback, unit_count)
        print(f"\n✅ saved → {OUT_DIR}")
    else:
        print("\n(DRY RUN — no save)")


if __name__ == "__main__":
    main()
