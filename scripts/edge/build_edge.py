"""
build_edge.py — STEP 4 EDGE FIELD (HANDOFF_v3 §8 + USER LOCK n7x4qp/n11)

DEFINITIONS (FINAL LOCK):
  r_t              := p_{t+1} - p_t       (p = log(close) → Δp = log return)
  E_state[i]       := E[r_t | Z_t = i]                  (β SYMMETRIC)
  E_transition[i,j]:= E[r_t | Z_t = i, Z_{t+1} = j]

INPUT (N12 채택):
  data/processed/state_vector/panel.parquet   (p column)
  data/processed/regime/regime.parquet        (Z_t)
  → (date, code) inner-join → [date, code, p, Z_t]

PROCEDURE:
  1) merge on (date, code), sort (code, date)
  2) per-code forward:
       p_{t+1}  = groupby(code).p.shift(-1)
       Z_{t+1}  = groupby(code).Z_t.shift(-1)
       r_t      = p_{t+1} - p_t
  3) valid mask (β SYMMETRIC):
       Z_t ≠ -1
       Z_{t+1} notna AND ≠ -1
       r_t notna
  4) E_state[i]        = mean(r_t | Z_t = i, valid)
     E_transition[i,j] = mean(r_t | Z_t = i, Z_{t+1} = j, valid)
  5) unobserved cells → NaN (N14: no fill)

VERIFY:
  algebraic identity (β 의 직접 귀결):
    E_state[i] ≡ Σ_j T[i,j] · E_transition[i,j]
  (T = STEP 3 산출. STEP 3 valid 조건 = STEP 4 valid 조건과 동일)

HARD CONSTRAINTS:
  • return 계산 외 feature 사용 금지
  • smoothing / clipping / winsorizing 금지
  • regime 기반 필터링 사전 적용 금지
  • negative EV 포함 상태 임의 제거 금지
  • 미관측 cell → NaN (no fill, no smoothing)

OUTPUT:
  data/processed/edge/E_state.npy       (shape (8,)   float64, NaN allowed)
  data/processed/edge/E_transition.npy  (shape (8,8)  float64, NaN allowed)
  data/processed/edge/N_state.npy       (shape (8,)   int64)
  data/processed/edge/N_transition.npy  (shape (8,8)  int64)
  data/processed/edge/meta.json
"""
import os, json, argparse
import numpy as np
import pandas as pd

# ============ PATHS ============
ROOT     = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SV_DIR   = os.path.join(ROOT, "data", "processed", "state_vector")
RG_DIR   = os.path.join(ROOT, "data", "processed", "regime")
TR_DIR   = os.path.join(ROOT, "data", "processed", "transition")
OUT_DIR  = os.path.join(ROOT, "data", "processed", "edge")

K_REGIME = 8


# ============ LOAD + MERGE (N12) ============
def load_merged():
    panel_p = os.path.join(SV_DIR, "panel.parquet")
    if not os.path.exists(panel_p):
        raise FileNotFoundError(panel_p)
    p_df = pd.read_parquet(panel_p, columns=["date", "code", "p"])
    p_df["date"] = pd.to_datetime(p_df["date"])

    rg_p = os.path.join(RG_DIR, "regime.parquet")
    if not os.path.exists(rg_p):
        raise FileNotFoundError(rg_p)
    rg_df = pd.read_parquet(rg_p, columns=["date", "code", "Z_t"])
    rg_df["date"] = pd.to_datetime(rg_df["date"])

    df = p_df.merge(rg_df, on=["date", "code"], how="inner")
    if len(df) != len(p_df) or len(df) != len(rg_df):
        print(f"  ⚠ merge size mismatch: merged={len(df):,} "
              f"panel={len(p_df):,} regime={len(rg_df):,}")
    df = df.sort_values(["code", "date"]).reset_index(drop=True)
    return df


# ============ FORWARD (r_t, Z_{t+1}) ============
def compute_forward(df):
    df = df.copy()
    g_p = df.groupby("code", sort=False)["p"].shift(-1)
    g_z = df.groupby("code", sort=False)["Z_t"].shift(-1)
    df["r_t"]    = g_p - df["p"]              # p_{t+1} - p_t
    df["Z_next"] = g_z                         # Z_{t+1}
    return df


# ============ E_state, E_transition (β SYMMETRIC) ============
def compute_edge(df):
    mask = (
        (df["Z_t"] != -1)
        & df["Z_next"].notna()
        & (df["Z_next"] != -1)
        & df["r_t"].notna()
    )
    valid = df.loc[mask, ["Z_t", "Z_next", "r_t"]].copy()
    valid["Z_t"]    = valid["Z_t"].astype(np.int64)
    valid["Z_next"] = valid["Z_next"].astype(np.int64)

    # E_state
    g_s = valid.groupby("Z_t")["r_t"]
    e_state_series = g_s.mean()
    n_state_series = g_s.size()
    E_state = np.full(K_REGIME, np.nan, dtype=np.float64)
    N_state = np.zeros(K_REGIME, dtype=np.int64)
    for i, v in e_state_series.items():
        E_state[int(i)] = float(v)
    for i, n in n_state_series.items():
        N_state[int(i)] = int(n)

    # E_transition
    E_trans = np.full((K_REGIME, K_REGIME), np.nan, dtype=np.float64)
    N_trans = np.zeros((K_REGIME, K_REGIME), dtype=np.int64)
    g_t = valid.groupby(["Z_t", "Z_next"])["r_t"]
    for (i, j), v in g_t.mean().items():
        E_trans[int(i), int(j)] = float(v)
    for (i, j), n in g_t.size().items():
        N_trans[int(i), int(j)] = int(n)

    return E_state, N_state, E_trans, N_trans, int(mask.sum())


# ============ IDENTITY CHECK ============
def load_T():
    p = os.path.join(TR_DIR, "T.npy")
    if not os.path.exists(p):
        raise FileNotFoundError(p)
    return np.load(p)


def identity_check(E_state, E_trans, T):
    """E_state[i] ≡ Σ_j T[i,j] · E_transition[i,j]
    
    T[i,j]=0 cell은 N_trans=0 → E_trans=NaN.
    0·NaN 회피: np.where(T>0, T*E_trans, 0)
    """
    contrib = np.where(T > 0, T * np.nan_to_num(E_trans, nan=0.0), 0.0)
    bad_mask = (T > 0) & np.isnan(E_trans)
    n_bad = int(bad_mask.sum())
    reconstruct = contrib.sum(axis=1)

    results = []
    max_d = 0.0
    for i in range(K_REGIME):
        if np.isnan(E_state[i]):
            row_sum_T = float(T[i].sum())
            results.append((i, None, float(reconstruct[i]), None,
                            f"E_state=NaN (N_state=0); T row sum={row_sum_T:.6f}"))
            continue
        d = abs(E_state[i] - reconstruct[i])
        max_d = max(max_d, d)
        results.append((i, float(E_state[i]), float(reconstruct[i]), d, None))
    return results, n_bad, max_d


# ============ VERIFY ============
def verify(E_state, N_state, E_trans, N_trans, n_valid, T, label_map):
    print("\n=== VERIFY ===")
    print(f"n_valid pairs   : {n_valid:,}")
    print(f"N_state sum     : {N_state.sum():,}")
    assert N_state.sum() == n_valid, f"ABORT: N_state sum mismatch ({N_state.sum()} vs {n_valid})"
    print(f"N_trans sum     : {N_trans.sum():,}")
    assert N_trans.sum() == n_valid, f"ABORT: N_trans sum mismatch ({N_trans.sum()} vs {n_valid})"
    print(f"observed states : {int((N_state > 0).sum())} / {K_REGIME}")
    print(f"observed trans  : {int((N_trans > 0).sum())} / {K_REGIME * K_REGIME}  "
          f"({(N_trans > 0).sum() / (K_REGIME * K_REGIME) * 100:.1f}%)")

    lm = {int(k): v for k, v in (label_map or {}).items()}

    print(f"\nE_state (forward log return per regime):")
    for i in range(K_REGIME):
        v = E_state[i]
        sv = "    NaN  " if np.isnan(v) else f"{v:+.6f}"
        # bps for intuition
        bps = "" if np.isnan(v) else f"  ({v*1e4:+.2f} bps/day)"
        print(f"  i={i}  N={N_state[i]:>8,}  E={sv}{bps}  | {lm.get(i, '?')}")

    print(f"\nE_transition (forward log return per (Z_t, Z_{{t+1}})):")
    hdr = "       " + "  ".join(f"   j={j}    " for j in range(K_REGIME))
    print(hdr + "  | label")
    for i in range(K_REGIME):
        cells = []
        for j in range(K_REGIME):
            v = E_trans[i, j]
            if np.isnan(v):
                cells.append("    NaN   ")
            else:
                cells.append(f"{v:+.5f}")
        print(f"  i={i} | " + "  ".join(cells) + f"  | {lm.get(i, '?')}")

    print(f"\nN_transition (visit counts):")
    for i in range(K_REGIME):
        cells = [f"{N_trans[i, j]:>8,}" for j in range(K_REGIME)]
        print(f"  i={i} | " + "  ".join(cells))

    # algebraic identity
    print(f"\n=== ALGEBRAIC IDENTITY CHECK ===")
    print("E_state[i] ?= Σ_j T[i,j] · E_transition[i,j]")
    results, n_bad, max_d = identity_check(E_state, E_trans, T)
    if n_bad > 0:
        print(f"  ⚠ T>0 but E_trans=NaN cells: {n_bad}")
    for r in results:
        if r[4] is not None:
            print(f"  i={r[0]}  ⚠ {r[4]}")
        else:
            i, es, rs, d, _ = r
            print(f"  i={i}  E_state={es:+.8f}  reconstruct={rs:+.8f}  Δ={d:.2e}")
    print(f"\n  max |Δ| = {max_d:.2e}")
    assert max_d < 1e-9, f"ABORT: identity broken (max Δ = {max_d:.2e})"
    print("  ✅ identity holds (max |Δ| < 1e-9)")


# ============ SAVE ============
def save_outputs(E_state, N_state, E_trans, N_trans, n_valid, label_map):
    os.makedirs(OUT_DIR, exist_ok=True)
    np.save(os.path.join(OUT_DIR, "E_state.npy"),      E_state)
    np.save(os.path.join(OUT_DIR, "E_transition.npy"), E_trans)
    np.save(os.path.join(OUT_DIR, "N_state.npy"),      N_state)
    np.save(os.path.join(OUT_DIR, "N_transition.npy"), N_trans)

    meta = {
        "n_valid_pairs"      : int(n_valid),
        "N_state"            : N_state.tolist(),
        "E_state"            : [None if np.isnan(v) else float(v) for v in E_state],
        "diag_E_transition"  : [None if np.isnan(v) else float(v) for v in E_trans.diagonal()],
        "observed_states"    : int((N_state > 0).sum()),
        "observed_trans"     : int((N_trans > 0).sum()),
        "trans_total_cells"  : int(K_REGIME * K_REGIME),
        "sparsity_trans"     : float((N_trans == 0).sum() / (K_REGIME * K_REGIME)),
        "label_map"          : {int(k): v for k, v in (label_map or {}).items()},
        "definitions": {
            "r_t"          : "p_{t+1} - p_t  where p = log(close)",
            "E_state"      : "E[r_t | Z_t = i]",
            "E_transition" : "E[r_t | Z_t = i, Z_{t+1} = j]",
            "inclusion"    : "β SYMMETRIC: Z_t != -1 AND Z_{t+1} != -1",
            "missing_cell" : "NaN (no fill, N14)",
        },
        "params": {"K_REGIME": K_REGIME},
    }
    with open(os.path.join(OUT_DIR, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)


# ============ MAIN ============
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print("[1/5] load + merge panel.p ↔ regime.Z_t on (date, code)")
    df = load_merged()
    print(f"      rows={len(df):,}  codes={df['code'].nunique()}  dates={df['date'].nunique()}")

    print("[2/5] forward (r_t = p_{t+1} - p_t, Z_next per code)")
    df = compute_forward(df)
    n_rnan = int(df["r_t"].isna().sum())
    n_znan = int(df["Z_next"].isna().sum())
    print(f"      r_t NaN (last row per code)    : {n_rnan:,}")
    print(f"      Z_next NaN (same boundary)     : {n_znan:,}")

    print("[3/5] compute E_state / E_transition (β SYMMETRIC, NaN unobserved)")
    E_state, N_state, E_trans, N_trans, n_valid = compute_edge(df)

    print("[4/5] load T (STEP 3) and identity check")
    T = load_T()

    lm_path = os.path.join(RG_DIR, "label_map.json")
    label_map = None
    if os.path.exists(lm_path):
        with open(lm_path) as f:
            label_map = json.load(f).get("label_map", {})

    verify(E_state, N_state, E_trans, N_trans, n_valid, T, label_map)

    print(f"\n[5/5] save")
    if not args.dry_run:
        save_outputs(E_state, N_state, E_trans, N_trans, n_valid, label_map)
        print(f"      ✅ saved → {OUT_DIR}")
    else:
        print("      (DRY RUN — no save)")


if __name__ == "__main__":
    main()
