"""
generate_signal.py — tradeable state matching -> signal output

입력:
  - data/cache/state_disc.parquet
  - model/deployment_config.json
  - scripts/universe_262.json

출력:
  - signals/YYYY-MM-DD.json
  - signals/YYYY-MM-DD.txt
  - stdout
"""
import os, sys, json, argparse
import pandas as pd

ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE      = os.path.join(ROOT, "data", "cache", "state_disc.parquet")
CONFIG     = os.path.join(ROOT, "model", "deployment_config.json")
UNIVERSE   = os.path.join(ROOT, "scripts", "universe_262.json")
SIGNAL_DIR = os.path.join(ROOT, "signals")

os.makedirs(SIGNAL_DIR, exist_ok=True)


def load_inputs():
    if not os.path.exists(CACHE):
        raise FileNotFoundError("state_disc not found. Run compute_state.py first.")
    if not os.path.exists(CONFIG):
        raise FileNotFoundError("deployment_config.json not found.")
    state_disc = pd.read_parquet(CACHE)
    state_disc["date"] = pd.to_datetime(state_disc["date"])
    state_disc = state_disc.set_index(["date","code"]).sort_index()
    with open(CONFIG) as f:
        cfg = json.load(f)
    with open(UNIVERSE) as f:
        univ = json.load(f)
    names = univ.get("names", {})
    return state_disc, cfg, names


def generate(state_disc, cfg, names, target_date=None):
    tradeable   = set(cfg["tradeable_states"])
    priority    = {int(k): float(v) for k, v in cfg["state_priority"].items()}
    max_n       = int(cfg["max_concurrent"])
    weight_each = 1.0 / max_n

    all_dates = state_disc.index.get_level_values("date").unique()
    if target_date is None:
        target = all_dates.max()
    else:
        target = pd.to_datetime(target_date)
        if target not in all_dates:
            raise ValueError(f"date {target_date} not in state_disc. "
                             f"available: {all_dates.min().date()} ~ {all_dates.max().date()}")

    day = state_disc.xs(target, level="date")[["state_id"]].copy()
    day = day.reset_index()
    day["code"] = day["code"].astype(str).str.zfill(6)

    matched = day[day["state_id"].isin(tradeable)].copy()
    matched["edge"]   = matched["state_id"].map(priority)
    matched["name"]   = matched["code"].map(names).fillna("(unknown)")
    matched["weight"] = weight_each
    matched = (matched.sort_values("edge", ascending=False)
                      .head(max_n).reset_index(drop=True))
    return target, matched


def render_json(target_date, matched):
    return {
        "date": target_date.strftime("%Y-%m-%d"),
        "n_signals": len(matched),
        "signals": [
            {
                "symbol":   row["code"],
                "state_id": int(row["state_id"]),
                "weight":   round(float(row["weight"]), 4),
                "edge":     round(float(row["edge"]), 6),
            }
            for _, row in matched.iterrows()
        ],
    }


def render_text(target_date, matched):
    lines = [f"[{target_date.strftime('%Y-%m-%d')}]"]
    if len(matched) == 0:
        lines.append("  (no signal)")
    else:
        lines.append(f"  signals: {len(matched)}")
        for _, r in matched.iterrows():
            lines.append(
                f"  BUY: {r['code']} {r['name']:<10s} "
                f"(state={r['state_id']}, edge={r['edge']:+.4f}, w={r['weight']:.2f})"
            )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None, help="YYYY-MM-DD")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    state_disc, cfg, names = load_inputs()
    target, matched = generate(state_disc, cfg, names, args.date)

    js  = render_json(target, matched)
    txt = render_text(target, matched)

    date_str = target.strftime("%Y-%m-%d")
    json_path = os.path.join(SIGNAL_DIR, f"{date_str}.json")
    text_path = os.path.join(SIGNAL_DIR, f"{date_str}.txt")
    with open(json_path, "w") as f:
        json.dump(js, f, indent=2, ensure_ascii=False)
    with open(text_path, "w") as f:
        f.write(txt + "\n")

    if not args.quiet:
        print(txt)
        print(f"\nsaved: {json_path}")
        print(f"saved: {text_path}")


if __name__ == "__main__":
    main()
