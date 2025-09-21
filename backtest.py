from main import *

def backtest_sector_pick(user_sector_key, risk_profile_key, eval_date, forward_days=252):
    """
    Backtests the model by pretending we picked stocks on eval_date
    and checking their performance over the next forward_days.
    """
    sp500 = fetch_sp500_table()
    sector_df = filter_by_user_sector(sp500, user_sector_key)
    if sector_df.empty:
        raise RuntimeError("No tickers found for sector.")
    tickers = sector_df['Symbol'].tolist()

    # download prices covering both lookback and forward window
    start_date = pd.to_datetime(eval_date) - pd.Timedelta(days=MOM_WINDOW_DAYS + 30)
    end_date = pd.to_datetime(eval_date) + pd.Timedelta(days=forward_days + 30)
    prices = yf.download(" ".join(tickers), start=start_date, end=end_date,
                         interval="1d", auto_adjust=True, threads=True)['Close']
    if isinstance(prices, pd.Series):
        prices = prices.to_frame(tickers[0])
    prices = prices.dropna(axis=1, how="all")

    # slice up to eval_date → score universe
    past_prices = prices.loc[:eval_date]
    if past_prices.empty:
        raise RuntimeError("No price data available up to eval_date.")

    # fundamentals (current, approximation since past fundamentals not available from Yahoo)
    fundamentals = []
    for t in past_prices.columns:
        try:
            tk = yf.Ticker(t)
            info = tk.get_info()
        except Exception:
            info = {}
        pe = info.get('trailingPE') or np.nan
        roe = info.get('returnOnEquity') or np.nan
        pm = info.get('profitMargins') or np.nan
        fundamentals.append({'Symbol': t, 'PE': pe, 'ROE': roe, 'ProfitMargin': pm})
    info_df = pd.DataFrame(fundamentals).set_index('Symbol')

    # scoring
    momentum = compute_momentum(past_prices)
    volatility = compute_volatility(past_prices)
    quality = compute_quality_score(info_df)
    value = compute_value_score(info_df)
    risk_penalty = compute_risk_penalty(volatility)

    mom_n = normalize_series(momentum, higher_is_better=True).fillna(0)
    val_n = value.fillna(0)
    qual_n = quality.fillna(0)
    risk_n = risk_penalty.fillna(1)

    w_m, w_v, w_q, w_r = RISK_PROFILE_WEIGHTS[risk_profile_key]
    raw_score = w_m * mom_n + w_v * val_n + w_q * qual_n - w_r * risk_n
    final_score = normalize_series(raw_score, higher_is_better=True)

    scored = pd.DataFrame({
        'Symbol': final_score.index,
        'Score': final_score.values
    }).merge(sector_df, on='Symbol', how='left')

    top_pick = scored.loc[scored['Score'].idxmax(), 'Symbol']

    # forward return
    eval_date = pd.to_datetime(eval_date).tz_localize(None)

    # pick closest available trading day
    if eval_date not in prices.index:
        eval_date = prices.index[prices.index.get_indexer([eval_date], method="nearest")[0]]

    start_price = prices.loc[eval_date, top_pick]

    forward_end_date = pd.to_datetime(eval_date) + pd.Timedelta(days=forward_days)
    forward_prices = prices.loc[eval_date:forward_end_date, top_pick].dropna()

    if forward_prices.empty:
        forward_return = np.nan
    else:
        forward_return = (forward_prices.iloc[-1] / start_price) - 1

    return top_pick, forward_return, scored



if __name__ == "__main__":
    print("BACKTEST: SELECT SECTOR, DATE, and RISK PROFILE to see return over 1 year from the backtest date")
    print("Sectors available:")
    for k in SECTOR_MAP.keys():
        print(" -", k)
    sector = input("Enter sector (one of the keys above): ").strip().lower()
    print("Risk Profiles: (Conservative, Moderate, Aggressive)")
    risk_profile = input("Enter risk profile: ").strip().lower()
    eval_date = input("Enter date(YYYY-MM-DD): ").strip()
    top, ret, scored = backtest_sector_pick(
        sector,
        risk_profile,
        eval_date,
        forward_days=252
    )
    print("\n" + f"Top pick on {eval_date}: {top}")
    print(f"Return over next year: {ret:.2%}")
    print(f"Evaluation date (nearest trading day): {eval_date}")
