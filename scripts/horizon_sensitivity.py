"""
horizon_sensitivity.py — Edge decay curve across hold horizons
LOCKED: simple return, overlapping, h ∈ {1,3,5,10,20,60}
"""
import os, sys, glob, json
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw", "ohlcv")
SV_DIR = os.path.join(ROOT, "data", "processed", "state_vector")
PN_DIR = os.path.join(ROOT, "data", "processed", "transition", "panel_with_regime")
OUT_DIR = os.path.join(ROOT, "data", "processed", "backtest")

TRAIN_END = pd.Timestamp("2022-12-31")
TEST_START = pd.Timestamp("2023-01-01")
MIN_VISITS, T_THRESHOLD = 100, 2.0
TRADEABLE_REG = {"TREND", "RANGE"}
COST_RT, ANN = 0.003, 252
HORIZONS = [1, 3, 5, 10, 20, 60]


def load_data():
    raw = pd.concat([pd.read_parquet(f, columns=["date","code","close"])
                     for f in sorted(glob.glob(f"{RAW_DIR}/year=*.parquet"))], ignore_index=True)
    raw["date"] = pd.to_datetime(raw["date"])
    sv = pd.concat([pd.read_parquet(f, columns=["date","code","state_id"])
                    for f in sorted(glob.glob(f"{SV_DIR}/year=*.parquet"))], ignore_index=True)
    sv["date"] = pd.to_datetime(sv["date"])
    pn = pd.concat([pd.read_parquet(f, columns=["date","code","regime"])
                    for f in sorted(glob.glob(f"{PN_DIR}/year=*.parquet"))], ignore_index=True)
    pn["date"] = pd.to_datetime(pn["date"])
    df = raw.merge(sv, on=["date","code"], how="inner").merge(pn, on=["date","code"], how="left")
    df = df.sort_values(["code","date"]).reset_index(drop=True)
    df["state_id"] = df["state_id"].astype(int)
    return df


def add_h(df, h):
    g = df.groupby("code", sort=False)
    df = df.copy(); df[f"ret_{h}"] = g["close"].shift(-h) / df["close"] - 1
    return df


def identify_tradeable(df, h):
    train = df[(df["date"]<=TRAIN_END) & df[f"ret_{h}"].notna()]
    g = train.groupby("state_id")
    stats = g.agg(visits=(f"ret_{h}","size"), mu_r=(f"ret_{h}","mean"), sigma_r=(f"ret_{h}","std")).reset_index()
    stats["t_stat"] = stats["mu_r"] / (stats["sigma_r"] / np.sqrt(stats["visits"]))
    rm = train.dropna(subset=["regime"]).groupby("state_id")["regime"].agg(lambda s: s.mode().iloc[0] if len(s) else None).to_dict()
    stats["regime"] = stats["state_id"].map(rm)
    mask = ((stats["mu_r"]>0) & (stats["visits"]>=MIN_VISITS) &
            (stats["t_stat"]>=T_THRESHOLD) & (stats["regime"].isin(TRADEABLE_REG)))
    return set(stats[mask]["state_id"].astype(int))


def backtest_h(df, h, tradeable):
    test = df[(df["date"]>=TEST_START) & df[f"ret_{h}"].notna()].copy()
    test["is_entry"] = test["state_id"].isin(tradeable)
    trades = test[test["is_entry"]].copy()
    if len(trades)==0: return None
    trades["ret_gross"] = trades[f"ret_{h}"]
    trades["ret_net"] = trades["ret_gross"] - COST_RT
    daily = trades.groupby("date").agg(ret_gross=("ret_gross","mean"), ret_net=("ret_net","mean")).reset_index()
    return trades, daily


def metrics(h, trades, daily):
    mu_g = trades["ret_gross"].mean()
    sd_d = daily["ret_gross"].std()
    mu_d = daily["ret_gross"].mean()
    mu_dn = daily["ret_net"].mean()
    sd_dn = daily["ret_net"].std()
    ann = ANN / h
    sh_g = (mu_d/sd_d)*np.sqrt(ann) if sd_d>0 else np.nan
    sh_n = (mu_dn/sd_dn)*np.sqrt(ann) if sd_dn>0 else np.nan
    win = (trades["ret_gross"]>0).mean()
    return {
        "h": h, "n_trades": int(len(trades)),
        "mu_gross_per_trade": round(float(mu_g),6),
        "mu_net_per_trade": round(float(mu_g - COST_RT),6),
        "win_rate": round(float(win),4),
        "sharpe_gross_ann": round(float(sh_g),3),
        "sharpe_net_ann": round(float(sh_n),3),
    }


def main():
    print("[load]"); df = load_data()
    print(f"  {len(df):,} rows")
    results = []
    for h in HORIZONS:
        print(f"\n[h={h}]")
        dfh = add_h(df, h)
        tr = identify_tradeable(dfh, h)
        print(f"  tradeable: {len(tr)}")
        if not tr: results.append({"h":h, "n_trades":0}); continue
        bt = backtest_h(dfh, h, tr)
        if bt is None: results.append({"h":h, "n_trades":0}); continue
        trades, daily = bt
        m = metrics(h, trades, daily); m["n_tradeable_states"] = len(tr)
        results.append(m)
    print("\n" + "="*90)
    print(f"{'h':>3}|{'states':>7}|{'trades':>7}|{'μ_gross':>10}|{'μ_net':>10}|{'win':>6}|{'sh_g':>7}|{'sh_n':>7}")
    print("-"*90)
    for r in results:
        if "sharpe_gross_ann" in r:
            print(f"{r['h']:>3}|{r['n_tradeable_states']:>7}|{r['n_trades']:>7}|"
                  f"{r['mu_gross_per_trade']:>10.6f}|{r['mu_net_per_trade']:>10.6f}|"
                  f"{r['win_rate']:>6.4f}|{r['sharpe_gross_ann']:>7.3f}|{r['sharpe_net_ann']:>7.3f}")
        else:
            print(f"{r['h']:>3}|{'-':>7}|{'-':>7}|{'-':>10}|{'-':>10}|{'-':>6}|{'-':>7}|{'-':>7}")
    print("="*90)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(f"{OUT_DIR}/horizon_sensitivity.json","w") as f: json.dump(results, f, indent=2)
    print("✅")


if __name__ == "__main__":
    main()
