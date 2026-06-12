"""STAGE 2 observe - CLI orchestration.

Subcommands:
  build    - attribution + diagnostics + viz
  summary  - attribution totals + by_regime
  class    - state class distribution + invariant states
  regime   - pnl_by_regime detail
  drift    - drift report summary
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.observation import attribution, classify, diagnostics, viz

OBS_DIR = Path("data/processed/observation")


def _read_json(p: Path):
    if not p.exists():
        sys.stderr.write(f"[observe] missing: {p}. Run 'observe build' first.\n")
        sys.exit(2)
    return json.loads(p.read_text())


def cmd_build(_):
    print("[observe] STAGE 2 build start")
    attribution.build()
    diagnostics.build()
    viz.build()
    print("[observe] STAGE 2 build done")


def cmd_summary(_):
    s = _read_json(OBS_DIR / "attribution_summary.json")
    print(json.dumps({
        "total_pnl":     s["total_pnl"],
        "ret_net":       s["ret_net"],
        "ret_gross":     s["ret_gross"],
        "pnl_by_regime": s["pnl_by_regime"],
    }, indent=2, ensure_ascii=False))


def cmd_class(_):
    print(json.dumps({
        "distribution":     classify.class_distribution(),
        "invariant_states": classify.invariant_states(),
    }, indent=2, default=str, ensure_ascii=False))


def cmd_regime(_):
    s = _read_json(OBS_DIR / "attribution_summary.json")
    print(json.dumps(s["pnl_by_regime"], indent=2, ensure_ascii=False))


def cmd_drift(_):
    d = _read_json(OBS_DIR / "drift_report.json")
    print(json.dumps({
        "kl_topN_size":             len(d["kl_topN"]),
        "kl_top5":                  d["kl_topN"][:5],
        "regime_frequency_change":  d["regime_frequency_change"],
        "state_distribution_split": d["state_distribution_shift"]["split_date"],
    }, indent=2, default=str, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(prog="observe",
                                 description="MSM observation CLI (STAGE 2).")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("build",   help="run attribution + diagnostics + viz")
    sp.add_parser("summary", help="attribution totals + by_regime")
    sp.add_parser("class",   help="state class distribution")
    sp.add_parser("regime",  help="regime PnL detail")
    sp.add_parser("drift",   help="drift report summary")
    args = ap.parse_args()
    {"build": cmd_build, "summary": cmd_summary,
     "class": cmd_class, "regime":  cmd_regime,
     "drift": cmd_drift}[args.cmd](args)


if __name__ == "__main__":
    main()
