"""
walk_forward_overlay.py — Walk-forward + Market Regime Overlay
LOCKED: universe-mean SMA-120, entry-only gating
NOTE: 실험 결과 overlay 무효 확인 (CV 악화). 보존용.
"""
import os, sys, glob, json
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw", "ohlcv")
SV_DIR = os.path.join(ROOT, "data", "processed", "state_vector")
PN_DIR = os.path.join(ROOT, "data", "processed", "transition", "panel_with_regime")
OUT_DIR = os.path.join(ROOT, "data", "processed", "backtest", "walk_forward_overlay")

H, COST_RT, ANN = 20, 0.003, 252
MIN_VISITS, T_THRESHOLD = 100, 2.0
TRADEABLE_REG = {"TREND", "RANGE"}
SMA_WINDOW = 120
TEST_YEARS = [2021, 2022, 2023, 2024, 2025, 2026]
PASS_SHARPE, PASS_MDD = 1.0, -0.30
SYS_MIN_PASS, SYS_MAX_CV, SYS_MIN_MEAN = 5, 0.5, 1.0


def load_all():
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


def build_market_regime(df):
    mkt = df.groupby("date")["close"].mean().reset_index().sort_values("date").reset_index(drop=True)
    mkt["sma"] = mkt["close"].rolling(SMA_WINDOW, min_periods=SMA_WINDOW).mean()
    mkt["is_bear"] = (mkt["close"] < mkt["sma"]).astype("Int64")
    mkt.loc[mkt["sma"].isna(), "is_bear"] = pd.NA
    return mkt


def identify_tradeable(train):
    g = train.groupby("state_id")
    stats = g.agg(visits=(f"ret_{H}","size"), mu_r=(f"ret_{H}","mean"), sigma_r=(f"ret_{H}","std")).reset_index()
    stats["t_stat"] = stats["mu_r"] / (stats["sigma_r"] / np.sqrt(stats["visits"]))
    rm = train.dropna(subset=["regime"]).groupby("state_id")["regime"].agg(lambda s: s.mode().iloc[0] if len(s) else None).to_dict()
    stats["regime"] = stats["state_id"].map(rm)
    mask = ((stats["mu_r"]>0) & (stats["visits"]>=MIN_VISITS) &
            (stats["t_stat"]>=T_THRESHOLD) & (stats["regime"].isin(TRADEABLE_REG)))
    return set(stats[mask]["state_id"].astype(int))


def gen_trades_overlay(test, tradeable, mkt):
    bear_map = mkt.set_index("date")["is_bear"].to_dict()
    cand = test[test["state_id"].isin(tradeable) & test[f"ret_{H}"].notna()].sort_values(["code","date"])
    trades = []
    for code, grp in cand.groupby("code", sort=False):
        last_exit = pd.Timestamp.min
        for _, row in grp.iterrows():
            if row["date"] <= last_exit: continue
            if bear_map.get(row["date"]) == 1: continue
            trades.append({"entry_date":row["date"], "exit_date":row["exit_date"],
                           "code":code, "state_id":row["state_id"], "regime":row["regime"],
                           "ret_gross":row[f"ret_{H}"]})
            last_exit = row["exit_date"]
    if not trades: return None
    tr = pd.DataFrame(trades); tr["ret_net"] = tr["ret_gross"] - COST_RT
    return tr


def portfolio(trades, df, start, end):
    test = df[(df["date"]>=start) & (df["date"]<=end)]
    all_dates = sorted(test["date"].unique())
    if not all_dates: return None
    didx = {d:i for i,d in enumerate(all_dates)}
    codes = trades["code"].unique()
    cdf = df[df["code"].isin(codes)][["code","date","close"]].sort_values(["code","date"])
    cdf["ret_d"] = cdf.groupby("code")["close"].pct_change()
    rmap = cdf.set_index(["code","date"])["ret_d"].to_dict()
    n = len(all_dates)
    daily_pnl = np.zeros(n); n_active = np.zeros(n, dtype=int)
    for _, tr in trades.iterrows():
        i_s = didx.get(tr["entry_date"]); i_e = didx.get(tr["exit_date"])
        if i_s is None: continue
        if i_e is None: i_e = n-1
        for i in range(i_s+1, i_e+1):
            r = rmap.get((tr["code"], all_dates[i]), 0.0)
            if pd.isna(r): r = 0.0
            daily_pnl[i] += r; n_active[i] += 1
        if i_e < n: daily_pnl[i_e] -= COST_RT
    with np.errstate(divide="ignore", invalid="ignore"):
        pr = np.where(n_active>0, daily_pnl/n_active, 0.0)
    eq = np.cumprod(1+pr)
    return all_dates, pr, eq, n_active


def fold_metrics(trades, port, year, n_blocked):
    if port is None or trades is None or len(trades)==0:
        return {"fold":year, "trades":0, "passed":False, "note":"no trades", "n_bear_blocked":n_blocked}
    dates, pr, eq, nact = port
    pra = pr[nact>0]
    if len(pra)<2: return {"fold":year, "trades":len(trades), "passed":False, "n_bear_blocked":n_blocked}
    mu, sd = pra.mean(), pra.std()
    sh = (mu/sd)*np.sqrt(ANN) if sd>0 else 0
    dd = eq/np.maximum.accumulate(eq) - 1
    mdd = dd.min()
    years = (dates[-1]-dates[0]).days/365.25
    cagr = (eq[-1]**(1/years)-1) if years>0 and eq[-1]>0 else 0
    passed = (sh>PASS_SHARPE) and (mdd>PASS_MDD)
    return {"fold":year, "trades":int(len(trades)), "n_bear_blocked":int(n_blocked),
            "sharpe_net":round(float(sh),3), "mdd":round(float(mdd),4),
            "cagr":round(float(cagr),4),
            "win_rate_net":round(float((trades["ret_net"]>0).mean()),4),
            "passed":bool(passed)}


def main():
    print("[load]"); df = load_all()
    mkt = build_market_regime(df)
    print(f"  bear days: {(mkt['is_bear']==1).sum()} / {mkt['is_bear'].notna().sum()}")
    fold_results = []; all_trades = []
    for ty in TEST_YEARS:
        train_end = pd.Timestamp(f"{ty-1}-12-31")
        start = pd.Timestamp(f"{ty}-01-01"); end = pd.Timestamp(f"{ty}-12-31")
        print(f"\n[FOLD {ty}]")
        train = df[(df["date"]<=train_end) & df[f"ret_{H}"].notna()]
        if len(train)==0: continue
        tradeable = identify_tradeable(train)
        if not tradeable:
            fold_results.append({"fold":ty, "trades":0, "passed":False}); continue
        test = df[(df["date"]>=start) & (df["date"]<=end)]
        fmkt = mkt[(mkt["date"]>=start) & (mkt["date"]<=end)]
        n_bear = int((fmkt["is_bear"]==1).sum())
        trades = gen_trades_overlay(test, tradeable, mkt)
        if trades is None:
            fold_results.append({"fold":ty, "trades":0, "passed":False, "n_bear_blocked":n_bear}); continue
        trades["fold"] = ty; all_trades.append(trades)
        port = portfolio(trades, df, start, end)
        m = fold_metrics(trades, port, ty, n_bear)
        fold_results.append(m)
        print(f"  {'✅' if m.get('passed') else '❌'} sh={m.get('sharpe_net','-')} mdd={m.get('mdd','-')} blocked={n_bear}")
    valid = [r for r in fold_results if "sharpe_net" in r]
    sharpes = [r["sharpe_net"] for r in valid]
    n_pass = sum(1 for r in fold_results if r.get("passed"))
    mean_s = float(np.mean(sharpes)) if sharpes else 0
    std_s = float(np.std(sharpes, ddof=1)) if len(sharpes)>1 else 0
    cv = std_s/mean_s if mean_s>0 else float("inf")
    sys_pass = (n_pass>=SYS_MIN_PASS) and (mean_s>SYS_MIN_MEAN) and (cv<SYS_MAX_CV)
    print("\n" + "="*80)
    print(f"  passed: {n_pass}/{len(fold_results)} | mean: {mean_s:.3f} | cv: {cv:.3f}")
    print(f"  SYSTEM: {'✅ PASS' if sys_pass else '❌ FAIL'}")
    print("="*80)
    os.makedirs(OUT_DIR, exist_ok=True)
    pd.DataFrame(fold_results).to_parquet(f"{OUT_DIR}/fold_results.parquet", index=False)
    if all_trades: pd.concat(all_trades, ignore_index=True).to_parquet(f"{OUT_DIR}/all_trades.parquet", index=False)
    mkt.to_parquet(f"{OUT_DIR}/market_regime.parquet", index=False)
    with open(f"{OUT_DIR}/summary.json","w") as f:
        json.dump({"fold_results":fold_results, "n_passed":n_pass, "mean_sharpe":round(mean_s,3),
                   "cv":round(cv,3) if not np.isinf(cv) else None, "system_pass":sys_pass}, f, indent=2)
    print("✅")


if __name__ == "__main__":
    main()
