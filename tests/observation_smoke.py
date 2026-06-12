"""STAGE 1 smoke test - import + load + class invariants. Hard fail."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.observation import loader, classify


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


if __name__ == "__main__":
    print("=== STAGE 1 smoke ===")
    for k, v in test_loaders().items():
        print(f"  load {k:18s} rows={v:>8,}")
    dist, inv = test_classify()
    print(f"  class dist = {dist}")
    print(f"  INVARIANT states = {inv}")
    print("=== OK ===")
