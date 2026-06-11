"""
fetch_daily.py — KRX OHLCV 일일 수집 (262 fixed universe)

사용법:
    python scripts/fetch_daily.py                # 마지막 거래일 이후 ~ 오늘
    python scripts/fetch_daily.py --date 20260611  # 특정 날짜만

특징:
    - idempotent (중복 실행 안전)
    - 262 fixed universe만 추출
    - 기존 schema 100% 유지
    - 등락률 직접 계산 (정밀도 일치)
"""
import os, sys, json, glob, argparse
import pandas as pd
from datetime import datetime, timedelta
from pykrx import stock

ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR  = os.path.join(ROOT, "data", "raw", "ohlcv")
UNIVERSE_FILE = os.path.join(os.path.dirname(__file__), "universe_262.json")

KR_TO_EN = {
    "시가":"open","고가":"high","저가":"low","종가":"close",
    "거래량":"volume","거래대금":"trade_value","등락률":"change_rate_pykrx",
}

def load_universe():
    with open(UNIVERSE_FILE) as f:
        meta = json.load(f)
    return set(meta["symbols"])

def get_last_date():
    files = sorted(glob.glob(f"{DATA_DIR}/year=*.parquet"))
    if not files:
        return None
    df = pd.read_parquet(files[-1], columns=["date"])
    return df["date"].max()

def fetch_market_day(date_yyyymmdd, market):
    """전종목 OHLCV 1일치"""
    df = stock.get_market_ohlcv(date_yyyymmdd, market=market)
    if df is None or df.empty:
        return None
    df = df.rename(columns=KR_TO_EN)
    df.index.name = "code"
    df = df.reset_index()
    df["code"] = df["code"].astype(str).str.zfill(6)
    df["date"] = pd.to_datetime(date_yyyymmdd).strftime("%Y-%m-%d")
    return df

def fetch_one_date(date_yyyymmdd, universe):
    """KOSPI + KOSDAQ 합치고 universe filter"""
    dfs = []
    for mkt in ["KOSPI", "KOSDAQ"]:
        df = fetch_market_day(date_yyyymmdd, mkt)
        if df is not None:
            dfs.append(df)
    if not dfs:
        return None
    combined = pd.concat(dfs, ignore_index=True)
    filtered = combined[combined["code"].isin(universe)].copy()
    return filtered

def compute_change_rate(df_new, existing_df):
    """change_rate를 prev close 기반으로 정확히 계산"""
    df_new = df_new.sort_values(["code","date"]).copy()
    # 종목별 prev close (existing의 최신 종가)
    if existing_df is not None and not existing_df.empty:
        last_close = (existing_df.sort_values("date")
                                 .groupby("code")["close"].last())
    else:
        last_close = pd.Series(dtype=float)

    df_new["prev_close"] = df_new["code"].map(last_close)
    # df_new 내 종목별 연쇄도 처리
    df_new["prev_close"] = df_new.groupby("code")["close"].shift(1).fillna(df_new["prev_close"])
    df_new["change_rate"] = ((df_new["close"] - df_new["prev_close"]) /
                              df_new["prev_close"] * 100)
    # 첫 거래일이거나 prev 없으면 pykrx 값 사용
    df_new["change_rate"] = df_new["change_rate"].fillna(df_new["change_rate_pykrx"])
    return df_new.drop(columns=["prev_close","change_rate_pykrx"])

def save_to_year_parquet(df_new):
    """연도별 parquet append (idempotent)"""
    if df_new is None or df_new.empty:
        return 0
    df_new["year"] = pd.to_datetime(df_new["date"]).dt.year
    saved = 0
    for year, grp in df_new.groupby("year"):
        path = f"{DATA_DIR}/year={year}.parquet"
        grp = grp.drop(columns=["year"])
        if os.path.exists(path):
            existing = pd.read_parquet(path)
            # 신규 (date, code) 만 추가
            keys_existing = set(zip(existing["date"], existing["code"]))
            new_only = grp[~grp.apply(lambda r: (r["date"], r["code"]) in keys_existing, axis=1)]
            if new_only.empty:
                continue
            combined = pd.concat([existing, new_only], ignore_index=True)
            combined = combined.sort_values(["date","code"]).reset_index(drop=True)
        else:
            combined = grp.sort_values(["date","code"]).reset_index(drop=True)
        # 기존 컬럼 순서 유지
        cols = ["date","open","high","low","close","volume","change_rate","code","trade_value"]
        combined = combined[cols]
        combined.to_parquet(path, index=False)
        saved += len(new_only) if os.path.exists(path) else len(grp)
    return saved

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None, help="YYYYMMDD (특정 날짜)")
    parser.add_argument("--from-date", default=None, help="YYYYMMDD")
    parser.add_argument("--to-date", default=None, help="YYYYMMDD")
    args = parser.parse_args()

    universe = load_universe()
    print(f"universe: {len(universe)} symbols")

    # 날짜 결정
    if args.date:
        dates = [args.date]
    elif args.from_date and args.to_date:
        # 영업일 범위
        bdays = stock.get_previous_business_days(
            fromdate=args.from_date, todate=args.to_date)
        dates = [d.strftime("%Y%m%d") for d in bdays]
    else:
        last = get_last_date()
        today = datetime.now().strftime("%Y%m%d")
        if last:
            start = (pd.to_datetime(last) + timedelta(days=1)).strftime("%Y%m%d")
        else:
            start = "20140101"
        bdays = stock.get_previous_business_days(fromdate=start, todate=today)
        dates = [d.strftime("%Y%m%d") for d in bdays]
        if not dates:
            print("이미 최신 상태 (마지막:", last, ")")
            return

    print(f"수집 대상: {len(dates)}일 ({dates[0]} ~ {dates[-1]})")

    total_added = 0
    for i, d in enumerate(dates, 1):
        df = fetch_one_date(d, universe)
        if df is None or df.empty:
            print(f"  [{i:3d}/{len(dates)}] {d}: 데이터 없음 (휴장?)")
            continue
        # 등락률 재계산
        year = pd.to_datetime(d).year
        existing_path = f"{DATA_DIR}/year={year}.parquet"
        existing_df = pd.read_parquet(existing_path) if os.path.exists(existing_path) else None
        df = compute_change_rate(df, existing_df)

        added = save_to_year_parquet(df)
        total_added += added
        print(f"  [{i:3d}/{len(dates)}] {d}: +{added}행 (universe matched: {len(df)})")

    print(f"\n✅ 완료: 총 {total_added}행 추가")

if __name__ == "__main__":
    main()
