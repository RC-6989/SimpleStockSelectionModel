import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import rankdata
import requests
import re
from functools import lru_cache

yf.set_tz_cache_location("~/.cache/yfinance")  # safer than None

MOM_WINDOW_DAYS = 252  # 12 months ~ 252 trading days
VOL_WINDOW_DAYS = 252  # volatility measured over 1 year

SECTOR_MAP = {
    "consumer cyclicals": ["Consumer Discretionary", "Consumer Cyclical", "Retail"],
    "banking/investment/finance": ["Financials", "Banks"],
    "energy/resources": ["Energy", "Utilities: Energy", "Utilities"],
    "industrial/manufacturing": ["Industrials"],
    "technology/telecommunications/utilities": ["Information Technology", "Telecommunication Services", "Technology", "Artificial Intelligence"],
    "healthcare": ["Health Care", "Healthcare"]
}

RISK_PROFILE_WEIGHTS = {
    "conservative": (0.10, 0.25, 0.40, 0.25),
    "moderate":    (0.25, 0.30, 0.30, 0.15),
    "aggressive":  (0.40, 0.20, 0.20, 0.20)
}

def fetch_sp500_table():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0"}
    html = requests.get(url, headers=headers, timeout=15).text
    tables = pd.read_html(html)
    df = tables[0].copy()
    df.columns = [c.strip() for c in df.columns]
    # find sector col robustly
    sector_col = next(c for c in df.columns if "Sector" in c)
    df = df.rename(columns={sector_col: "Sector"})
    # clean symbols like BRK.B
    df['Symbol'] = (
        df['Symbol']
        .astype(str)
        .str.replace(r'\s+\*.*$', '', regex=True)
        .str.replace('.', '-', regex=False)
    )
    return df[['Symbol', 'Security', 'Sector']]

def filter_by_user_sector(sp500_df, user_sector_key):
    allowed = SECTOR_MAP.get(user_sector_key.lower())
    if allowed is None:
        raise ValueError(f"Unknown sector: {user_sector_key}")
    mask = sp500_df['Sector'].apply(lambda s: any(a.lower() in s.lower() for a in allowed))
    return sp500_df[mask].reset_index(drop=True)

from functools import lru_cache

@lru_cache(maxsize=512)
def _get_info_cached(t):
    try:
        return yf.Ticker(t).get_info()
    except Exception:
        return {}

def fetch_tickers_data(tickers):
    tickers_str = " ".join(tickers)
    prices = yf.download(
        tickers_str,
        period="1y",
        interval="1d",
        auto_adjust=True,
        threads=True
    )['Close']
    if isinstance(prices, pd.Series):
        prices = prices.to_frame(tickers[0])
    prices = prices.dropna(axis=1, how="all")  # drop failed downloads

    fundamentals = []
    for t in prices.columns:
        info = _get_info_cached(t)
        pe = info.get('trailingPE') or info.get('priceToEarningsTrailing12Months') or np.nan
        roe = info.get('returnOnEquity') or np.nan
        pm = info.get('profitMargins') or info.get('operatingMargins') or info.get('grossMargins') or np.nan
        fundamentals.append({'Symbol': t, 'PE': pe, 'ROE': roe, 'ProfitMargin': pm})
    info_df = pd.DataFrame(fundamentals).set_index('Symbol')
    return prices, info_df


def compute_momentum(prices, lookback=MOM_WINDOW_DAYS):
    p = prices.dropna(how="all")
    if p.empty:
        return pd.Series(index=p.columns, data=np.nan)

    last_date = p.index[-1]
    target_date = last_date - pd.Timedelta(days=lookback)
    if target_date not in p.index:
        target_date = p.index[p.index.get_indexer([target_date], method="nearest")[0]]

    ret_long = (p.loc[last_date] / p.loc[target_date]) - 1
    # blend with shorter-term (3 month) momentum for stability
    short_window = 63
    short_target = last_date - pd.Timedelta(days=short_window)
    if short_target not in p.index:
        short_target = p.index[p.index.get_indexer([short_target], method="nearest")[0]]
    ret_short = (p.loc[last_date] / p.loc[short_target]) - 1

    ret = 0.75 * ret_long + 0.25 * ret_short
    # winsorize extreme outliers
    cap = np.nanpercentile(ret, [5, 95])
    ret = ret.clip(lower=cap[0], upper=cap[1])
    return ret

def compute_volatility(prices, window=VOL_WINDOW_DAYS):
    daily_ret = prices.pct_change().dropna(how='all')
    if daily_ret.empty:
        return pd.Series(index=prices.columns, data=np.nan)
    vol_std = daily_ret.std() * np.sqrt(252)
    vol_ewma = daily_ret.ewm(span=63).std().iloc[-1] * np.sqrt(252)
    vol = 0.5 * vol_std + 0.5 * vol_ewma
    cap = np.nanpercentile(vol, [5, 95])
    vol = vol.clip(lower=cap[0], upper=cap[1])
    return vol

def normalize_series(s, higher_is_better=True):
    s_clean = s.copy().astype(float)
    if s_clean.dropna().empty:
        return pd.Series(index=s.index, data=np.nan)
    ranks = rankdata(s_clean.fillna(s_clean.min() - 1))  # put NaNs below min
    denom = np.nanmax(ranks) - np.nanmin(ranks)
    if denom == 0:
        norm = pd.Series(index=s.index, data=0.5)  # all same value → flat 0.5
    else:
        norm = (ranks - np.nanmin(ranks)) / denom
        norm = pd.Series(index=s.index, data=norm)
    if not higher_is_better:
        norm = 1 - norm
    norm[s.isna()] = np.nan
    return norm

def compute_quality_score(info_df):
    roe_n = normalize_series(info_df['ROE'], higher_is_better=True)
    pm_n = normalize_series(info_df['ProfitMargin'], higher_is_better=True)
    return 0.5 * roe_n + 0.5 * pm_n

def compute_value_score(info_df):
    pe = info_df['PE'].replace({0: np.nan, np.inf: np.nan, -np.inf: np.nan})
    inv_pe = 1 / pe
    # winsorize extreme values
    cap = np.nanpercentile(inv_pe, [5, 95])
    inv_pe = inv_pe.clip(lower=cap[0], upper=cap[1])
    return normalize_series(inv_pe, higher_is_better=True)


def compute_risk_penalty(vol_series):
    return normalize_series(vol_series, higher_is_better=True)

def score_universe(tickers, sector_df, risk_profile):
    prices, info = fetch_tickers_data(tickers)
    if prices.empty:
        raise RuntimeError("No valid price data downloaded.")

    momentum = compute_momentum(prices, lookback=MOM_WINDOW_DAYS)
    volatility = compute_volatility(prices, window=VOL_WINDOW_DAYS)
    quality = compute_quality_score(info)
    value = compute_value_score(info)
    risk_penalty = compute_risk_penalty(volatility)

    mom_n = normalize_series(momentum, higher_is_better=True)
    val_n = value
    qual_n = quality
    risk_n = risk_penalty

    idx = sorted(set(mom_n.index) | set(val_n.index) | set(qual_n.index) | set(risk_n.index))
    mom_n, val_n, qual_n, risk_n = mom_n.reindex(idx), val_n.reindex(idx), qual_n.reindex(idx), risk_n.reindex(idx)

    mom_n, val_n, qual_n = mom_n.fillna(0), val_n.fillna(0), qual_n.fillna(0)
    risk_n = risk_n.fillna(risk_n.max() if not np.isnan(risk_n.max()) else 1)

    w_m, w_v, w_q, w_r = RISK_PROFILE_WEIGHTS[risk_profile]
    raw_score = w_m * mom_n + w_v * val_n + w_q * qual_n - w_r * risk_n
    final_score = normalize_series(raw_score, higher_is_better=True)

    result = pd.DataFrame({
        'Symbol': idx,
        'Momentum': mom_n.values,
        'Value': val_n.values,
        'Quality': qual_n.values,
        'RiskPenalty': risk_n.values,
        'RawScore': raw_score.values,
        'Score': final_score.values
    })
    result = result.merge(sector_df[['Symbol', 'Security', 'Sector']], on='Symbol', how='left')
    return result.sort_values('Score', ascending=False)

def pick_top_stock_for_sector(user_sector_key, risk_profile_key):
    sp500 = fetch_sp500_table()
    sector_df = filter_by_user_sector(sp500, user_sector_key)
    if sector_df.empty:
        raise RuntimeError("No tickers found for sector.")
    tickers = sector_df['Symbol'].tolist()
    print(f"Found {len(tickers)} tickers in sector '{user_sector_key}'. Downloading data...")
    scored = score_universe(tickers, sector_df, risk_profile_key)
    return scored.iloc[0], scored

if __name__ == "__main__":
    print("Sectors available:")
    for k in SECTOR_MAP.keys():
        print(" -", k)
    user_sector = input("Enter sector (one of the keys above): ").strip().lower()
    print("\nRisk profiles: conservative, moderate, aggressive")
    rp = input("Enter risk profile: ").strip().lower()
    if rp not in RISK_PROFILE_WEIGHTS:
        print("Unknown risk profile. Defaulting to 'moderate'.")
        rp = 'moderate'
    top, df = pick_top_stock_for_sector(user_sector, rp)
    print("\nTop pick:")
    print(top.to_string())

    safe_user_sector = re.sub(r'[^A-Za-z0-9_-]', '_', user_sector)
    safe_rp = re.sub(r'[^A-Za-z0-9_-]', '_', str(rp))
    filename = f"scored_{safe_user_sector}_{safe_rp}.csv"
    df.to_csv(filename, index=False)
    print(f"\nFull scored list saved to {filename}")
