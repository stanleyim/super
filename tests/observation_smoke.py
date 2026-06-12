"""STAGE 1 + STAGE 2 smoke (D5 = c).

G2 additions:
  - recursive finite check on attribution_summary.json + drift_report.json
  - parquet column finite check on attribution.parquet
"""
import json, math, subprocess, sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.observation import attribution, classify, diagnostics, loader, viz

OBS = Path("data/processed/observation")


# --- helpers (G2) ---
def _assert_recursive_finite(obj, path: str = "$") -> None:
    """Hard-fail if any float in nested dict/list is NaN or +/-inf."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            _assert_recursive_finite(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _assert_recursive_finite(v, f"{path}[{i}]")
    elif isinstance(obj, float):
        if not math.isfinite(obj):
            raise AssertionError(f"[G2] non-finite float at {path}: {obj!r}")


# --- STAGE 1 ---
def test_loaders():
    sizes = {
        "state_class":      len(loader.load_state_class()),
        "regime_pnl":       len(loader.load_regime_pnl()),
        "state_decomp":     len(loader.load_state_decomp()),
        "ev_flip_map":      len(loader.load_ev_flip()),
        "regime_labels":    len(loader.load_regime_labels()),
        "transition_drift": len(loader.load_transition_drift()),
        "transition_kl":    len(loader.load_transition_kl()),
        "panel":            len(loader.load_panel()),
        "trades":           len(loader.load_trades()),
    }
    for k, v in sizes.items():
        assert v > 0, f"{k} empty"
    return sizes


def test_classify():
    dist = classify.class_distribution()
    assert dist["INVARIANT"] >= 1, f"INVARIANT regression: {dist}"
    assert dist["TRAP"]      == 0, f"TRAP unexpected: {dist}"
    return dist, classify.invariant_states()


# --- STAGE 2 ---
ATTR_KEYS = {"total_pnl", "ret_net", "ret_gross", "pnl_by_regime",
             "pnl_by_state", "pnl_by_asset",
             "top_contributors", "worst_contributors"}
DRIFT_KEYS = {"kl_topN", "p_stay", "transition_shift_matrix",
              "regime_frequency_change", "state_distribution_shift"}


def test_attribution_run():
    df = attribution.build()
    assert (OBS / "attribution.parquet").exists()
    assert (OBS / "attribution_summary.json").exists()
    s = json.loads((OBS / "attribution_summary.json").read_text())
    missing = ATTR_KEYS - set(s.keys())
    assert not missing, f"attribution_summary missing keys: {missing}"
    # G2: recursive finite check
    _assert_recursive_finite(s, "$.attribution_summary")
    # G2: parquet column finite check
    df_parq = pd.read_parquet(OBS / "attribution.parquet")
    for c in ("ret_net", "ret_gross"):
        arr = df_parq[c].to_numpy()
        assert np.isfinite(arr).all(), f"[G2] attribution.parquet.{c} non-finite"
    return len(df)


def test_diagnostics_run():
    d = diagnostics.build()
    assert (OBS / "diagnostics_kl_topN.json").exists()
    assert (OBS / "drift_report.json").exists()
    missing = DRIFT_KEYS - set(d.keys())
    assert not missing, f"drift_report missing keys: {missing}"
    assert len(d["kl_topN"]) <= 50
    # G2: recursive finite check on both JSONs (re-read from disk)
    kl_disk    = json.loads((OBS / "diagnostics_kl_topN.json").read_text())
    drift_disk = json.loads((OBS / "drift_report.json").read_text())
    _assert_recursive_finite(kl_disk,    "$.diagnostics_kl_topN")
    _assert_recursive_finite(drift_disk, "$.drift_report")
    return {k: (len(v) if hasattr(v, "__len__") else "ok") for k, v in d.items()}


def test_viz_run():
    out = viz.build()
    successes = [v for v in out.values() if v is not None]
    assert len(successes) >= 1, f"all viz failed: {out}"
    return out


def test_observe_cli():
    root = Path(__file__).resolve().parents[1]
    cmd = [sys.executable, str(root / "scripts" / "observe.py"), "summary"]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=root)
    assert res.returncode == 0, f"CLI summary failed rc={res.returncode}\n{res.stderr}"
    payload = json.loads(res.stdout)
    assert "total_pnl" in payload
    _assert_recursive_finite(payload, "$.cli_summary")
    return "ok"


if __name__ == "__main__":
    print("=== STAGE 1 smoke ===")
    for k, v in test_loaders().items():
        print(f"  load {k:18s} rows={v:>8,}")
    dist, inv = test_classify()
    print(f"  class dist = {dist}")
    print(f"  INVARIANT states = {inv}")
    print("=== STAGE 2 smoke (G2 guards on) ===")
    n = test_attribution_run()
    print(f"  attribution rows = {n:,}")
    sizes = test_diagnostics_run()
    print(f"  diagnostics      = {sizes}")
    out = test_viz_run()
    print(f"  viz              = {out}")
    cli = test_observe_cli()
    print(f"  observe CLI      = {cli}")
    print("=== OK ===")
