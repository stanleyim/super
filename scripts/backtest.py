"""
backtest.py — h=1 Out-of-Sample (STEP 9 baseline)
LOCKED: equal-weight, 0.3% cost, train 2015-2022 / test 2023-
"""
import os, sys, glob, json, argparse
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL_DIR = os.path.join(ROOT, "data", "processed", "transition", "panel_with_regime")
OUT_DIR   = os.path.join(ROOT, "data", "processed", "backtest")

TRAIN_END = pd.Timestamp("2022-12-31")
TEST_START = pd.Timestamp("2023-01-01")
MIN_VISITS, T_THRESHOLD = 100, 2.0
TRADEABLE_REG = {"TREND", "RANGE"}
COST_RT, ANN = 0.003, 252


def load_panel():
    files = sorted(glob.glob(f"{PANEL_DIR}/year=*.parquet"))
    if not files: raise FileNotFoundError(PANEL_DIR)
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["date","code"]).reset_index(drop=True)


def identify_tradeable(panel):
    train = panel[panel["date"] <= TRAIN_END]
    print(f"  train: {len(train):,} rows")
    g = train.groupby("state_id")
    stats = g.agg(visits=("next_r","size"), mu_r=("next_r","mean"), sigma_r=("next_r","std")).reset_index()
    stats["t_stat"] = stats["mu_r"] / (stats["sigma_r"] / np.sqrt(stats["visits"]))
    rm = train.groupby("state_id")["regime"].agg(lambda s: s.mode().iloc[0]).to_dict()
    stats["regime"] = stats["state_id"].map(rm)
    mask = ((stats["mu_r"]>0) & (stats["visits"]>=MIN_VISITS) &
            (stats["t_stat"]>=T_THRESHOLD) & (stats["regime"].isin(TRADEABLE_REG)))
    tr = stats[mask]
    print(f"  tradeable: {len(tr)}")
    return set(tr["state_id"].astype(int)), stats


def run_backtest(panel, tradeable_set):
    test = panel[panel["date"] >= TEST_START].copy()
    print(f"  test: {len(test):,} rows")
    test["is_entry"] = test["state_id"].astype(int).isin(tradeable_set)
    trades = test[test["is_entry"]].copy()
    if len(trades) == 0: return None, None, None
    trades = trades[["date","code","state_id","regime","next_r"]].rename(columns={"next_r":"ret_gross"})
    daily = trades.groupby("date").agg(n_trades=("ret_gross","size"), ret_gross=("ret_gross","mean")).reset_index()
    daily["cost"] = COST_RT
    daily["ret_net"] = daily["ret_gross"] - daily["cost"]
    daily["cum_gross"] = (1+daily["ret_gross"]).cumprod() - 1
    daily["cum_net"] = (1+daily["ret_net"]).cumprod() - 1
    return trades, daily, test


def compute_metrics(trades, daily, test):
    mu_g, sd_g = daily["ret_gross"].mean(), daily["ret_gross"].std()
    mu_n, sd_n = daily["ret_net"].mean(), daily["ret_net"].std()
    sh_g = (mu_g/sd_g)*np.sqrt(ANN) if sd_g>0 else np.nan
    sh_n = (mu_n/sd_n)*np.sqrt(ANN) if sd_n>0 else np.nan
    cum = (1+daily["ret_net"]).cumprod()
    dd = cum / cum.cummax() - 1
    mdd = dd.min()
    win_g = (trades["ret_gross"]>0).mean()
    years = (daily["date"].iloc[-1] - daily["date"].iloc[0]).days / 365.25
    final = daily["cum_net"].iloc[-1]
    cagr = (1+final)**(1/years)-1 if years>0 else np.nan
    return {
        "n_trades": int(len(trades)),
        "mean_ret_gross_daily": round(float(mu_g),6),
        "mean_ret_net_daily": round(float(mu_n),6),
        "sharpe_gross_ann": round(float(sh_g),3),
        "sharpe_net_ann": round(float(sh_n),3),
        "win_rate_gross": round(float(win_g),4),
        "mdd": round(float(mdd),4),
        "final_cum_net": round(float(final),4),
        "cagr_net": round(float(cagr),4) if not np.isnan(cagr) else None,
        "cost_rt": COST_RT,
    }


def main():
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    print("[load]"); panel = load_panel()
    print(f"  {len(panel):,} rows")
    print("[train identify]")
    tradeable, _ = identify_tradeable(panel)
    if not tradeable: print("❌ no tradeable"); sys.exit(1)
    print("[test backtest]")
    trades, daily, test = run_backtest(panel, tradeable)
    if trades is None: print("❌ no trades"); sys.exit(1)
    m = compute_metrics(trades, daily, test)
    print("\n" + "="*60)
    for k,v in m.items(): print(f"  {k}: {v}")
    print("="*60)
    os.makedirs(OUT_DIR, exist_ok=True)
    if not args.dry_run:
        trades.to_parquet(f"{OUT_DIR}/trades.parquet", index=False)
        daily.to_parquet(f"{OUT_DIR}/daily_pnl.parquet", index=False)
        with open(f"{OUT_DIR}/summary.json","w") as f: json.dump(m, f, indent=2)
    print("✅")


if __name__ == "__main__":
    main()
