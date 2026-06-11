"""
fetch_daily_v2.py — MSM-grade KRX OHLCV daily ingestion
"""
import os, sys, json, glob, argparse
import pandas as pd
from datetime import datetime, timedelta
from pykrx import stock

ROOT          = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR      = os.path.join(ROOT, "data", "raw", "ohlcv")
UNIVERSE_FILE = os.path.join(os.path.dirname(__file__), "universe_262.json")

COLS = ["date", "open", "high", "low", "close", "volume",
        "change_rate", "code", "trade_value"]

KR_TO_EN = {
    "시가": "open", "고가": "high", "저가": "low", "종가": "close",
    "거래량": "volume", "거래대금": "trade_value", "등락률": "change_rate_pykrx",
}


def load_universe():
    with open(UNIVERSE_FILE) as f:
        return set(json.load(f)["symbols"])


def get_last_date():
    files = sorted(glob.glob(f"{DATA_DIR}/year=*.parquet"))
    if not files: return None
    df = pd.read_parquet(files[-1], columns=["date"])
    return pd.to_datetime(df["date"]).max()


def fetch_market_day(date_yyyymmdd, market):
    df = stock.get_market_ohlcv(date_yyyymmdd, market=market)
    if df is None or df.empty: return None
    df = df.rename(columns=KR_TO_EN)
    df.index.name = "code"
    df = df.reset_index()
    df["code"] = df["code"].astype(str).str.zfill(6)
    df["date"] = pd.to_datetime(date_yyyymmdd)
    return df


def fetch_one_date(date_yyyymmdd, universe):
    dfs = []
    for mkt in ["KOSPI", "KOSDAQ"]:
        df = fetch_market_day(date_yyyymmdd, mkt)
        if df is not None: dfs.append(df)
    if not dfs: return None
    combined = pd.concat(dfs, ignore_index=True)
    return combined[combined["code"].isin(universe)].copy()


def get_prev_close_map(year, data_dir):
    out = {}
    for y in [year - 1, year]:
        path = f"{data_dir}/year={y}.parquet"
        if not os.path.exists(path): continue
        df = pd.read_parquet(path, columns=["date", "code", "close"])
        df["date"] = pd.to_datetime(df["date"])
        last = df.sort_values("date").groupby("code")["close"].last().to_dict()
        out.update(last)
    return out


def compute_change_rate(df_new, prev_close_map, cold_start_log=None):
    df_new = df_new.sort_values(["code", "date"]).copy()
    df_new["prev_close"] = df_new["code"].map(prev_close_map)
    chain = df_new.groupby("code")["close"].shift(1)
    df_new["prev_close"] = chain.fillna(df_new["prev_close"])
    df_new["change_rate"] = ((df_new["close"] - df_new["prev_close"]) / df_new["prev_close"] * 100)
    mask_cold = df_new["change_rate"].isna()
    if mask_cold.any() and cold_start_log is not None:
        n = int(mask_cold.sum())
        sample = df_new.loc[mask_cold, "code"].unique().tolist()[:5]
        cold_start_log.append(f"cold start: {n} rows | sample: {sample}")
    df_new["change_rate"] = df_new["change_rate"].fillna(df_new["change_rate_pykrx"])
    return df_new.drop(columns=["prev_close", "change_rate_pykrx"])


def save_to_year_parquet(df_new, data_dir, dry_run=False):
    if df_new is None or df_new.empty: return 0
    df_new = df_new.copy()
    df_new["date"] = pd.to_datetime(df_new["date"])
    df_new["__year"] = df_new["date"].dt.year
    total_added = 0
    for year, grp in df_new.groupby("__year"):
        path = f"{data_dir}/year={year}.parquet"
        grp = grp.drop(columns=["__year"]).copy()
        if os.path.exists(path):
            existing = pd.read_parquet(path)
            existing["date"] = pd.to_datetime(existing["date"])
            ex_keys = (existing["date"].dt.strftime("%Y-%m-%d") + "_" + existing["code"].astype(str)).values
            gr_keys = (grp["date"].dt.strftime("%Y-%m-%d") + "_" + grp["code"].astype(str)).values
            mask_new = ~pd.Series(gr_keys).isin(ex_keys).values
            new_only = grp[mask_new]
            if new_only.empty: continue
            combined = pd.concat([existing, new_only], ignore_index=True)
            n_added = len(new_only)
        else:
            combined = grp
            n_added = len(grp)
        combined = combined.sort_values(["date", "code"]).reset_index(drop=True)[COLS]
        if not dry_run: combined.to_parquet(path, index=False)
        total_added += n_added
    return total_added


def verify_ingestion(data_dir, universe):
    files = sorted(glob.glob(f"{data_dir}/year=*.parquet"))
    if not files: print("[verify] no files"); return False
    parts = []
    for f in files:
        df = pd.read_parquet(f)
        df["date"] = pd.to_datetime(df["date"])
        parts.append(df)
    full = pd.concat(parts, ignore_index=True)
    leaked = set(full["code"].unique()) - set(universe)
    if leaked:
        print(f"[verify] ❌ universe LEAK: {len(leaked)} codes")
        return False
    full = full.sort_values(["code", "date"]).reset_index(drop=True)
    full["prev_close"] = full.groupby("code")["close"].shift(1)
    full["recomputed"] = (full["close"] - full["prev_close"]) / full["prev_close"] * 100
    full["diff"] = (full["change_rate"] - full["recomputed"]).abs()
    full["yr"] = full["date"].dt.year
    full["pyr"] = full.groupby("code")["date"].shift(1).dt.year
    boundary = full[(full["yr"] != full["pyr"]) & full["pyr"].notna()]
    bad = boundary[boundary["diff"] > 0.01]
    if len(bad) > 0:
        print(f"[verify] ❌ year boundary issues: {len(bad)}")
        return False
    print(f"[verify] ✅ PASS | rows: {len(full):,} | codes: {full['code'].nunique()}")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None)
    parser.add_argument("--from-date", default=None)
    parser.add_argument("--to-date", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    universe = load_universe()
    print(f"universe: {len(universe)} symbols")
    if args.verify:
        sys.exit(0 if verify_ingestion(DATA_DIR, universe) else 1)

    if args.date:
        dates = [args.date]
    elif args.from_date and args.to_date:
        bdays = stock.get_previous_business_days(fromdate=args.from_date, todate=args.to_date)
        dates = [d.strftime("%Y%m%d") for d in bdays]
    else:
        last = get_last_date()
        today = datetime.now().strftime("%Y%m%d")
        start = ((last + timedelta(days=1)).strftime("%Y%m%d") if last is not None else "20140101")
        bdays = stock.get_previous_business_days(fromdate=start, todate=today)
        dates = [d.strftime("%Y%m%d") for d in bdays]
        if not dates: print(f"이미 최신: {last}"); return

    mode = " [DRY-RUN]" if args.dry_run else ""
    print(f"수집 {len(dates)}일{mode}")
    cold_log = []
    total = 0
    for i, d in enumerate(dates, 1):
        df = fetch_one_date(d, universe)
        if df is None or df.empty:
            print(f"  [{i}/{len(dates)}] {d}: 휴장"); continue
        year = pd.to_datetime(d).year
        prev_map = get_prev_close_map(year, DATA_DIR)
        df = compute_change_rate(df, prev_map, cold_log)
        added = save_to_year_parquet(df, DATA_DIR, dry_run=args.dry_run)
        total += added
        print(f"  [{i}/{len(dates)}] {d}: +{added}")
    if cold_log:
        print("\n⚠ cold starts:")
        for l in cold_log: print(f"  - {l}")
    print(f"\n✅ 완료: +{total}{mode}")


if __name__ == "__main__":
    main()
