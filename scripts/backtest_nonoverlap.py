"""
backtest_nonoverlap.py — h=20 Non-Overlapping Portfolio (STEP 9 final)
LOCKED: per-code blocking, entry-time fixed equal-weight, infinite capital
"""
import os, sys, glob, json
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw", "ohlcv")
SV_DIR = os.path.join(ROOT, "data", "processed", "state_vector")
PN_DIR = os.path.join(ROOT, "data", "processed", "transition", "panel_with_regime")
OUT_DIR = os.path.join(ROOT, "data", "processed", "backtest", "h20_nonoverlap")

TRAIN_END = pd.Timestamp("2022-12-31")
TEST_START = pd.Timestamp("2023-01-01")
H, COST_RT, ANN = 20, 0.003, 252
MIN_VISITS, T_THRESHOLD = 100, 2.0
TRADEABLE_REG = {"TREND", "RANGE"}


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
    g = df.groupby("code", sort=False)
    df[f"ret_{H}"] = g["close"].shift(-H) / df["close"] - 1
    df["exit_date"] = g["date"].shift(-H)
    return df


def identify_tradeable(df):
    train = df[(df["date"]<=TRAIN_END) & df[f"ret_{H}"].notna()]
    g = train.groupby("state_id")
    stats = g.agg(visits=(f"ret_{H}","size"), mu_r=(f"ret_{H}","mean"), sigma_r=(f"ret_{H}","std")).reset_index()
    stats["t_stat"] = stats["mu_r"] / (stats["sigma_r"] / np.sqrt(stats["visits"]))
    rm = train.dropna(subset=["regime"]).groupby("state_id")["regime"].agg(lambda s: s.mode().iloc[0] if len(s) else None).to_dict()
    stats["regime"] = stats["state_id"].map(rm)
    base = (stats["visits"]>=MIN_VISITS) & (stats["regime"].isin(TRADEABLE_REG))
    long_mask  = base & (stats["t_stat"] >=  T_THRESHOLD)
    short_mask = base & (stats["t_stat"] <= -T_THRESHOLD)
    out = {}
    for sid in stats[long_mask]["state_id"].astype(int):  out[int(sid)] = "L"
    for sid in stats[short_mask]["state_id"].astype(int): out[int(sid)] = "S"
    return out


def gen_trades(df, tradeable):
    test = df[(df["date"]>=TEST_START) & df[f"ret_{H}"].notna()].copy()
    cand = test[test["state_id"].isin(tradeable.keys())].sort_values(["code","date"])
    trades = []
    for code, grp in cand.groupby("code", sort=False):
        last_exit = pd.Timestamp.min      # per-code blocking (L+S unified)
        for _, row in grp.iterrows():
            if row["date"] <= last_exit: continue
            sid = int(row["state_id"])
            trades.append({"entry_date":row["date"], "exit_date":row["exit_date"],
                           "code":code, "state_id":sid, "regime":row["regime"],
                           "side":tradeable[sid], "ret_gross":row[f"ret_{H}"]})
            last_exit = row["exit_date"]
    if not trades: return None
    tr = pd.DataFrame(trades)
    sign = np.where(tr["side"].values=="S", -1.0, 1.0)
    tr["ret_net"] = sign * tr["ret_gross"] - COST_RT
    return tr


def portfolio_path(trades, df):
    test = df[df["date"]>=TEST_START]
    all_dates = sorted(test["date"].unique())
    didx = {d:i for i,d in enumerate(all_dates)}
    codes = trades["code"].unique()
    cdf = df[df["code"].isin(codes)][["code","date","close"]].sort_values(["code","date"])
    cdf["ret_d"] = cdf.groupby("code")["close"].pct_change()
    rmap = cdf.set_index(["code","date"])["ret_d"].to_dict()
    n = len(all_dates)
    daily_pnl = np.zeros(n); n_active = np.zeros(n, dtype=int)
    for _, tr in trades.iterrows():
        i_s = didx.get(tr["entry_date"]); i_e = didx.get(tr["exit_date"])
        if i_s is None or i_e is None: continue
        s = -1.0 if tr.get("side","L")=="S" else 1.0
        for i in range(i_s+1, i_e+1):
            r = rmap.get((tr["code"], all_dates[i]), 0.0)
            if pd.isna(r): r = 0.0
            daily_pnl[i] += s*r; n_active[i] += 1
        if i_e < n and n_active[i_e] > 0: daily_pnl[i_e] -= COST_RT
    with np.errstate(divide="ignore", invalid="ignore"):
        pr = np.where(n_active>0, daily_pnl/n_active, 0.0)
    eq = np.cumprod(1+pr)
    return pd.DataFrame({"date":all_dates, "n_active":n_active, "port_ret":pr, "equity":eq})


def metrics(trades, port):
    pr = port["port_ret"].values
    pr_a = pr[port["n_active"]>0]
    mu, sd = pr_a.mean(), pr_a.std()
    sh = (mu/sd)*np.sqrt(ANN) if sd>0 else np.nan
    ds = pr_a[pr_a<0]
    ds_sd = ds.std() if len(ds)>1 else np.nan
    sortino = (mu/ds_sd)*np.sqrt(ANN) if ds_sd and ds_sd>0 else np.nan
    eq = port["equity"].values
    dd = eq/np.maximum.accumulate(eq) - 1
    mdd = dd.min()
    years = (port["date"].iloc[-1] - port["date"].iloc[0]).days / 365.25
    cagr = (eq[-1]**(1/years)-1) if years>0 and eq[-1]>0 else np.nan
    calmar = cagr/abs(mdd) if mdd<0 and not np.isnan(cagr) else np.nan
    return {
        "n_trades": int(len(trades)),
        "win_rate_net": round(float((trades["ret_net"]>0).mean()),4),
        "avg_active": round(float(port["n_active"].mean()),2),
        "sharpe_net_ann": round(float(sh),3) if not np.isnan(sh) else None,
        "sortino_net_ann": round(float(sortino),3) if sortino and not np.isnan(sortino) else None,
        "mdd": round(float(mdd),4),
        "cagr": round(float(cagr),4) if not np.isnan(cagr) else None,
        "calmar": round(float(calmar),3) if calmar and not np.isnan(calmar) else None,
        "final_equity": round(float(eq[-1]),4),
        "horizon_days": H, "cost_rt": COST_RT,
    }


def main():
    print("[load]"); df = load_data()
    print(f"  {len(df):,} rows")
    tradeable = identify_tradeable(df)
    print(f"[tradeable] {len(tradeable)}")
    if not tradeable: sys.exit(1)
    trades = gen_trades(df, tradeable)
    print(f"[trades] {len(trades):,}")
    port = portfolio_path(trades, df)
    m = metrics(trades, port)
    print("\n" + "="*60)
    for k,v in m.items(): print(f"  {k}: {v}")
    print("="*60)
    os.makedirs(OUT_DIR, exist_ok=True)
    trades.to_parquet(f"{OUT_DIR}/trades.parquet", index=False)
    port.to_parquet(f"{OUT_DIR}/daily_portfolio.parquet", index=False)
    with open(f"{OUT_DIR}/summary.json","w") as f: json.dump(m, f, indent=2)
    print("✅")


if __name__ == "__main__":
    main()
