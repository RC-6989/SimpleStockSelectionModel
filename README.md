##S&P 500 Factor Model & Backtesting

This repository contains a Python system for selecting S&P 500 stocks using a factor-based ranking model and performing backtests. The model combines Momentum, Valuation, Quality, and Volatility factors, weighted by user-defined risk profiles.

O#verview

The project consists of two main files:

main.py – Fetches stock data, computes factor scores, and ranks stocks.

backtest.py – Provides a CLI to backtest and evaluate stock picks.

The model ranks stocks based on normalized factor scores, weighted according to the user’s risk profile.

#Factor Model

Overall Score for a stock i:

Score_i = NormalizeRank( w_m * M_i + w_v * V_i + w_q * Q_i - w_r * R_i )


Where:

M_i = Momentum factor

V_i = Valuation factor

Q_i = Quality factor

R_i = Volatility / Risk penalty

w_m, w_v, w_q, w_r = weights based on risk profile

Momentum Factor (M_i)
M_i = NormalizeRank( 0.75 * ((P_i(t) / P_i(t-252)) - 1) 
                   + 0.25 * ((P_i(t) / P_i(t-63)) - 1) )


P_i(t) = price on evaluation date

P_i(t-252) = price ~1 year ago (252 trading days)

P_i(t-63) = price ~1 quarter ago (63 trading days)

Valuation Factor (V_i)
V_i = NormalizeRank( 1 / PE_i )


PE_i = price-to-earnings ratio

Higher 1/PE means better value (earnings yield)

Quality Factor (Q_i)
Q_i = 0.5 * NormalizeRank(ROE_i) + 0.5 * NormalizeRank(ProfitMargin_i)


ROE_i = Return on Equity

ProfitMargin_i = Net profit margin

Volatility / Risk Penalty (R_i)
R_i = NormalizeRank(Volatility_i)


Volatility is annualized standard deviation of daily returns:

Volatility_i = std(daily_returns) * sqrt(252)

Normalization

All factors are converted to a 0–1 scale using rank normalization:

NormalizeRank(X_i) = (rank(X_i) - min(rank(X))) / (max(rank(X)) - min(rank(X)))


Best stock in a factor = 1, worst = 0

For factors where lower is better (Volatility, P/E), the ranking is inverted

Final Score Interpretation

Score_i combines all normalized factors using the selected weights.

Higher scores indicate better stock picks.

Volatility reduces the score for high-risk stocks.

#CLI Usage

Run the backtesting tool:

python backtest.py


#The CLI allows you to:

Select a sector from the S&P 500.
Select a risk profile: Conservative, Moderate, or Aggressive.
Enter an evaluation date.
Optionally specify the forward horizon (default 252 trading days).

#The CLI outputs:

Top stock pick for the sector and date
Estimated return over the forward horizon
CSV of the full scored universe

#Example: 

Enter sector: technology

Enter risk profile: moderate

Enter date (YYYY-MM-DD): 2025-06-30


Output:

Top pick on 2025-06-30: AAPL
Return over next year: 12.35%
Full scored list saved to scored_technology_moderate.csv


#Notes:

- Uses Yahoo Finance APIs for data.
- Momentum uses 252-day (1 year) and 63-day (1 quarter) returns.
- Quality factor uses ROE and Profit Margin.
- Volatility is annualized to penalize high-risk stocks.
- Risk profile weights are configurable in main.py.
