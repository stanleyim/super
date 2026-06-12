"""STAGE 2 viz - matplotlib charts to reports/.

Charts:
  regime_pnl.png         - ret_net + ret_gross by regime
  class_distribution.png - state class counts
  kl_topN.png            - top-50 by kl_bull_bear

Inputs are pre-validated upstream (attribution/diagnostics G2 guards).
"""
import json
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from scripts.observation import classify

OBS_DIR      = Path("data/processed/observation")
ATTR_SUMMARY = OBS_DIR / "attribution_summary.json"
KL_PATH      = OBS_DIR / "diagnostics_kl_topN.json"
REPORTS      = Path("reports")


def _regime_pnl_chart() -> Path:
    s = json.loads(ATTR_SUMMARY.read_text())
    by_reg = s["pnl_by_regime"]
    regimes = sorted(set(list(by_reg["ret_net"].keys()) +
                         list(by_reg["ret_gross"].keys())))
    net   = [by_reg["ret_net"].get(r, 0.0)   for r in regimes]
    gross = [by_reg["ret_gross"].get(r, 0.0) for r in regimes]
    fig, ax = plt.subplots(figsize=(8, 5))
    x = list(range(len(regimes))); w = 0.4
    ax.bar([i - w/2 for i in x], gross, w, label="ret_gross")
    ax.bar([i + w/2 for i in x], net,   w, label="ret_net")
    ax.set_xticks(x); ax.set_xticklabels(regimes)
    ax.set_ylabel("PnL sum"); ax.set_title("Regime PnL (gross vs net)")
    ax.axhline(0, color="black", lw=0.5); ax.legend(); ax.grid(alpha=0.3, axis="y")
    out = REPORTS / "regime_pnl.png"
    fig.tight_layout(); fig.savefig(out, dpi=120); plt.close(fig)
    return out


def _class_distribution_chart() -> Path:
    dist = classify.class_distribution()
    classes = list(dist.keys()); counts = [dist[c] for c in classes]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(classes, counts)
    ax.set_ylabel("state count"); ax.set_title("State Class Distribution")
    for i, c in enumerate(counts):
        ax.text(i, c, str(c), ha="center", va="bottom")
    ax.grid(alpha=0.3, axis="y")
    out = REPORTS / "class_distribution.png"
    fig.tight_layout(); fig.savefig(out, dpi=120); plt.close(fig)
    return out


def _kl_topN_chart() -> Path:
    kl = json.loads(KL_PATH.read_text())
    df = pd.DataFrame(kl).sort_values("kl_bull_bear", ascending=True)
    fig, ax = plt.subplots(figsize=(8, max(6.0, len(df) * 0.2)))
    ax.barh(df["state_id"].astype(str), df["kl_bull_bear"])
    ax.set_xlabel("KL(bull || bear)")
    ax.set_title(f"Top {len(df)} states by KL divergence (BULL vs BEAR)")
    ax.grid(alpha=0.3, axis="x")
    out = REPORTS / "kl_topN.png"
    fig.tight_layout(); fig.savefig(out, dpi=120); plt.close(fig)
    return out


def build() -> dict:
    REPORTS.mkdir(parents=True, exist_ok=True)
    results = {}
    for name, fn in [
        ("regime_pnl",         _regime_pnl_chart),
        ("class_distribution", _class_distribution_chart),
        ("kl_topN",            _kl_topN_chart),
    ]:
        try:
            results[name] = str(fn())
        except Exception as e:
            warnings.warn(f"viz/{name} failed: {e}")
            results[name] = None
    return results


if __name__ == "__main__":
    for k, v in build().items():
        print(f"  {k}: {v}")
