import numpy as np
import pandas as pd
from main import (
    SECTOR_MAP,
    fetch_sp500_table,
    filter_by_user_sector,
    MOM_WINDOW_DAYS,
    RISK_PROFILE_WEIGHTS,
    compute_momentum,
    compute_volatility,
    compute_quality_score,
    compute_value_score,
    compute_risk_penalty,
    normalize_series
)
import yfinance as yf
import time, re

# --- Utilities (same as before, for robustness) ---
def _safe_yf_download(tickers_str, **kwargs):
    attempts, backoff, last_err = 3, 1.0, None
    for i in range(attempts):
        try:
            data = yf.download(tickers_str, **kwargs)
            if isinstance(data, pd.DataFrame) and 'Close' in data.columns:
                return data['Close']
            else:
                return data
        except Exception as e:
            last_err = e
            time.sleep(backoff)
            backoff *= 2
    raise RuntimeError(f"yf.download failed after {attempts} attempts. Last error: {last_err}")

def _safe_ticker_info(ticker):
    try:
        tk = yf.Ticker(ticker)
        return tk.get_info() or {}
    except Exception:
        return {}

def _safe_filename(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s)

# --- Core backtest function (same as before) ---
def backtest_sector_pick(user_sector_key, risk_profile_key, eval_date, forward_days=252, save_csv=True, verbose=True):
    sp500 = fetch_sp500_table()
    sector_df = filter_by_user_sector(sp500, user_sector_key)
    if sector_df.empty:
        raise RuntimeError("No tickers found for sector.")
    tickers = sector_df['Symbol'].tolist()

    eval_date_ts = pd.to_datetime(eval_date)
    start_date = eval_date_ts - pd.Timedelta(days=MOM_WINDOW_DAYS + 30)
    end_date = eval_date_ts + pd.Timedelta(days=forward_days + 30)

    if verbose:
        print(f"\nDownloading price history for {len(tickers)} tickers from {start_date.date()} to {end_date.date()}...")

    tickers_str = " ".join(tickers)
    prices = _safe_yf_download(tickers_str, start=start_date, end=end_date, interval="1d", auto_adjust=True, threads=True)

    if isinstance(prices, pd.Series):
        prices = prices.to_frame(tickers[0])
    prices = prices.dropna(axis=1, how="all")
    if prices.empty:
        raise RuntimeError("No price data downloaded for any tickers in this sector.")

    if hasattr(prices.index, 'tz') and prices.index.tz is not None:
        prices.index = prices.index.tz_localize(None)

    if eval_date_ts not in prices.index:
        nearest_pos = prices.index.get_indexer([eval_date_ts], method="nearest")[0]
        used_eval_date = prices.index[nearest_pos]
        if verbose:
            print(f"Requested eval_date {eval_date} not a trading day; using nearest trading day {used_eval_date.date()}.")
    else:
        used_eval_date = eval_date_ts

    past_prices = prices.loc[:used_eval_date]
    if past_prices.empty:
        raise RuntimeError("No price data available up to eval_date.")

    fundamentals = []
    for t in past_prices.columns:
        info = _safe_ticker_info(t)
        pe = info.get('trailingPE') or np.nan
        roe = info.get('returnOnEquity') or np.nan
        pm = info.get('profitMargins') or np.nan
        fundamentals.append({'Symbol': t, 'PE': pe, 'ROE': roe, 'ProfitMargin': pm})
    info_df = pd.DataFrame(fundamentals).set_index('Symbol')

    momentum = compute_momentum(past_prices)
    volatility = compute_volatility(past_prices)
    quality = compute_quality_score(info_df)
    value = compute_value_score(info_df)
    risk_penalty = compute_risk_penalty(volatility)

    mom_n = normalize_series(momentum, higher_is_better=True).fillna(0)
    val_n = value.fillna(0)
    qual_n = quality.fillna(0)
    risk_n = risk_penalty.fillna(risk_penalty.median() if not risk_penalty.dropna().empty else 0.5)

    w_m, w_v, w_q, w_r = RISK_PROFILE_WEIGHTS[risk_profile_key]
    raw_score = w_m * mom_n + w_v * val_n + w_q * qual_n - w_r * risk_n
    final_score = normalize_series(raw_score, higher_is_better=True)

    scored = pd.DataFrame({'Symbol': final_score.index, 'Score': final_score.values}).merge(sector_df, on='Symbol', how='left')

    if save_csv:
        fname = f"scored_{_safe_filename(user_sector_key)}_{_safe_filename(risk_profile_key)}_{used_eval_date.date()}.csv"
        scored.to_csv(fname, index=False)
        if verbose:
            print(f"Scored universe saved to {fname}")

    if scored['Score'].isna().all():
        raise RuntimeError("All scores are NaN.")
    top_pick = scored.loc[scored['Score'].idxmax(), 'Symbol']

    start_price = prices.loc[used_eval_date, top_pick]
    forward_end_date = used_eval_date + pd.Timedelta(days=forward_days)
    if forward_end_date not in prices.index:
        idx = prices.index.get_indexer([forward_end_date], method="nearest")[0]
        forward_end_idx = min(idx, len(prices)-1)
    else:
        forward_end_idx = prices.index.get_loc(forward_end_date)
    forward_prices = prices.iloc[prices.index.get_loc(used_eval_date): forward_end_idx+1][top_pick].dropna()

    forward_return = (forward_prices.iloc[-1] / start_price) - 1 if not forward_prices.empty else np.nan
    return top_pick, forward_return, scored

# --- Improved CLI ---
if __name__ == "__main__":
    print("="*50)
    print("📊  S&P 500 Sector Backtest Tool")
    print("="*50)

    # Sector menu
    sectors = list(SECTOR_MAP.keys())
    print("\nSectors:")
    for i, s in enumerate(sectors, 1):
        print(f" {i}. {s}")
    while True:
        try:
            sec_choice = int(input("\nEnter sector number: "))
            if 1 <= sec_choice <= len(sectors):
                sector = sectors[sec_choice-1]
                break
        except:
            pass
        print("Invalid choice. Please enter a valid number.")

    # Risk profile menu
    profiles = list(RISK_PROFILE_WEIGHTS.keys())
    print("\nRisk Profiles:")
    for i, r in enumerate(profiles, 1):
        print(f" {i}. {r}")
    while True:
        try:
            rp_choice = int(input("\nEnter risk profile number: "))
            if 1 <= rp_choice <= len(profiles):
                risk_profile = profiles[rp_choice-1]
                break
        except:
            pass
        print("Invalid choice. Please enter a valid number.")

    eval_date = input("\nEnter evaluation date (YYYY-MM-DD): ").strip()
    forward_days_str = input("Forward test horizon days [default=252]: ").strip()
    forward_days = int(forward_days_str) if forward_days_str else 252

    print("\nRunning backtest...")
    top, ret, scored = backtest_sector_pick(
        sector,
        risk_profile,
        eval_date,
        forward_days=forward_days,
        save_csv=True,
        verbose=True
    )

    print("\n"+"="*50)
    print(f"Top pick on {eval_date}: {top}")
    if not np.isnan(ret):
        print(f"Return over next {forward_days} days: {ret:.2%}")
    else:
        print(f"Forward return not available (insufficient data)")
    print("="*50)
    print("Check saved CSV for full scored universe.")
