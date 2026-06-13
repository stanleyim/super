"""
build_transition.py — STEP 3 TRANSITION ESTIMATION (LOCKED SPEC, HANDOFF_v3 §7)

INPUT (§7.1):
  data/processed/regime/regime.parquet  (Z_t column only)
  - 사용 금지: T_HMM, X_cont, X_norm, features, R_t

PROCEDURE (§7.2):
  1) valid (t→t+1) iff:
       Z_t != -1, Z_{t+1} != -1, same code
       (Q3-(b): same-subseq는 sentinel + same-code 검사로 충분)
  2) C[i,j] = pooled count across all assets
  3) row-normalize:
       if row_sum > 0: T[i] = C[i] / row_sum
       else:           T[i] = 0-vector  (no imputation)

HARD CONSTRAINTS (§7.4):
  • pure empirical frequency only
  • zero-row 보정 금지
  • subsequence boundary 침범 금지
  • sentinel(-1) 포함 transition 금지
  • HMM 파라미터 일체 사용 금지
  • feature / state reconstruction 금지
  • smoothing / regularization / prior / threshold filtering 전부 금지

OUTPUT (§7.3):
  data/processed/transition/T.npy       (8×8 float64)
  data/processed/transition/C.npy       (8×8 int64, diagnostic)
  data/processed/transition/meta.json
"""
import os, json, argparse
import numpy as np
import pandas as pd

# ============ PATHS ============
ROOT     = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RG_DIR   = os.path.join(ROOT, "data", "processed", "regime")
OUT_DIR  = os.path.join(ROOT, "data", "processed", "transition")

K_REGIME = 8


# ============ LOAD ============
def load_regime():
    p = os.path.join(RG_DIR, "regime.parquet")
    if not os.path.exists(p):
        raise FileNotFoundError(p)
    df = pd.read_parquet(p, columns=["date", "code", "Z_t"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["code", "date"]).reset_index(drop=True)
    return df


# ============ COUNT (§7.2 step 1-2, Q3-(b) 해석) ============
def count_transitions(df):
    """
    valid pair (Z_t → Z_{t+1}):
      • Z_t != -1
      • Z_{t+1} != -1
      • same code (groupby + shift(-1) → boundary 자동 NaN 처리)
    """
    df = df.copy()
    df["Z_curr"] = df["Z_t"]
    df["Z_next"] = df.groupby("code", sort=False)["Z_t"].shift(-1)

    mask = (
        (df["Z_curr"] != -1)
        & df["Z_next"].notna()
        & (df["Z_next"] != -1)
    )
    pairs = df.loc[mask, ["Z_curr", "Z_next"]].astype(np.int64)

    C = np.zeros((K_REGIME, K_REGIME), dtype=np.int64)
    np.add.at(
        C,
        (pairs["Z_curr"].to_numpy(), pairs["Z_next"].to_numpy()),
        1,
    )
    return C, int(mask.sum())


# ============ NORMALIZE (§7.2 step 3-4) ============
def normalize(C):
    T = np.zeros_like(C, dtype=np.float64)
    row_sums = C.sum(axis=1)
    for i in range(K_REGIME):
        if row_sums[i] > 0:
            T[i] = C[i].astype(np.float64) / row_sums[i]
        # else: T[i] = 0-vector  (zero-init 유지, 보정 금지)
    return T, row_sums


# ============ VERIFY (§7.3 properties) ============
def verify(T, C, row_sums, n_transitions, label_map):
    print("\n=== VERIFY ===")
    print(f"n_transitions  : {n_transitions:,}")
    print(f"C row sums     : {row_sums.tolist()}")
    print(f"C col sums     : {C.sum(axis=0).tolist()}")
    print(f"observed rows  : {int((row_sums > 0).sum())} / {K_REGIME}")
    print(f"zero rows      : {int((row_sums == 0).sum())}")

    print(f"\nT shape        : {T.shape}")
    print(f"T row sums     : {T.sum(axis=1).round(6).tolist()}")
    print(f"T value range  : [{T.min():.6f}, {T.max():.6f}]")
    print(f"diagonal       : {T.diagonal().round(4).tolist()}")
    print(f"mean p_stay    : {T.diagonal().mean():.4f}")

    # property assertions
    assert T.shape == (K_REGIME, K_REGIME), "ABORT: T shape"
    assert (T >= 0).all(), "ABORT: T has negative"
    for i in range(K_REGIME):
        s = T[i].sum()
        if row_sums[i] > 0:
            assert abs(s - 1.0) < 1e-9, f"ABORT: row {i} sum={s}, expected 1"
        else:
            assert s == 0.0, f"ABORT: row {i} sum={s}, expected 0"
    print("✅ properties: T[i,j]≥0, Σ_j T[i,j] ∈ {0,1}")

    # full matrices
    lm = {int(k): v for k, v in (label_map or {}).items()}
    print(f"\nT matrix (rows = from, cols = to):")
    header = "         " + "  ".join(f"  j={j}  " for j in range(K_REGIME)) + "   | label"
    print(header)
    for i in range(K_REGIME):
        row = "  ".join(f"{T[i, j]:.4f}" for j in range(K_REGIME))
        print(f"  i={i} |  {row}   | {lm.get(i, '?')}")

    print(f"\nC matrix:")
    for i in range(K_REGIME):
        row = "  ".join(f"{C[i, j]:>8,}" for j in range(K_REGIME))
        print(f"  i={i} | {row}")


# ============ SAVE ============
def save_outputs(T, C, row_sums, n_transitions, label_map):
    os.makedirs(OUT_DIR, exist_ok=True)
    np.save(os.path.join(OUT_DIR, "T.npy"), T)
    np.save(os.path.join(OUT_DIR, "C.npy"), C)

    meta = {
        "n_transitions"     : int(n_transitions),
        "row_sums"          : [int(s) for s in row_sums],
        "n_observed_rows"   : int((row_sums > 0).sum()),
        "n_zero_rows"       : int((row_sums == 0).sum()),
        "diagonal_p_stay"   : T.diagonal().tolist(),
        "mean_p_stay"       : float(T.diagonal().mean()),
        "sparsity_T"        : float((T == 0).sum() / T.size),
        "label_map"         : {int(k): v for k, v in (label_map or {}).items()},
        "params"            : {"K_REGIME": K_REGIME},
    }
    with open(os.path.join(OUT_DIR, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)


# ============ MAIN ============
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print("[1/4] load_regime")
    df = load_regime()
    print(f"      rows={len(df):,}  codes={df['code'].nunique()}  dates={df['date'].nunique()}")
    n_inv = int((df["Z_t"] == -1).sum())
    print(f"      Z_t=-1 (invalid) : {n_inv:,}  ({n_inv/len(df)*100:.2f}%)")

    print("[2/4] count_transitions (per-asset, sentinel + group boundary)")
    C, n_trans = count_transitions(df)
    print(f"      n_transitions   : {n_trans:,}")

    print("[3/4] normalize (zero-row preserved as 0-vector)")
    T, row_sums = normalize(C)

    # label_map.json (read-only, verify display 용도, computation 미사용)
    label_map = None
    lm_path = os.path.join(RG_DIR, "label_map.json")
    if os.path.exists(lm_path):
        with open(lm_path) as f:
            label_map = json.load(f).get("label_map", {})

    verify(T, C, row_sums, n_trans, label_map)

    print(f"\n[4/4] save")
    if not args.dry_run:
        save_outputs(T, C, row_sums, n_trans, label_map)
        print(f"      ✅ saved → {OUT_DIR}")
    else:
        print("      (DRY RUN — no save)")


if __name__ == "__main__":
    main()
