S&P 500 Factor Model & Backtesting

This repository contains a Python system for selecting S&P 500 stocks using a factor-based ranking model and performing backtests. The model combines momentum, valuation, quality, and volatility factors with user-defined risk profiles.

Overview

The project consists of two main files:

main.py – Fetches stock data, computes factor scores, and ranks stocks.

backtest.py – Provides a command-line interface (CLI) to backtest and evaluate stock picks.

The model ranks stocks based on normalized factor scores, weighted according to the user’s risk profile.

Factor Model

The overall score for stock i is:

Score
𝑖
=
NormalizeRank
(
𝑤
𝑚
𝑀
𝑖
+
𝑤
𝑣
𝑉
𝑖
+
𝑤
𝑞
𝑄
𝑖
−
𝑤
𝑟
𝑅
𝑖
)
Score
i
	​

=NormalizeRank(w
m
	​

M
i
	​

+w
v
	​

V
i
	​

+w
q
	​

Q
i
	​

−w
r
	​

R
i
	​

)

Where:

𝑀
𝑖
M
i
	​

 = Momentum factor

𝑉
𝑖
V
i
	​

 = Valuation factor

𝑄
𝑖
Q
i
	​

 = Quality factor

𝑅
𝑖
R
i
	​

 = Risk / Volatility penalty

𝑤
𝑚
,
𝑤
𝑣
,
𝑤
𝑞
,
𝑤
𝑟
w
m
	​

,w
v
	​

,w
q
	​

,w
r
	​

 = weights defined by the selected risk profile

Momentum Factor (
𝑀
𝑖
M
i
	​

)

Momentum is a combination of long-term (1 year) and short-term (1 quarter) returns:

𝑀
𝑖
=
NormalizeRank
(
0.75
⋅
𝑃
𝑖
(
𝑡
)
𝑃
𝑖
(
𝑡
−
252
)
−
1
+
0.25
⋅
𝑃
𝑖
(
𝑡
)
𝑃
𝑖
(
𝑡
−
63
)
−
1
)
M
i
	​

=NormalizeRank(0.75⋅
P
i
	​

(t−252)
P
i
	​

(t)
	​

−1+0.25⋅
P
i
	​

(t−63)
P
i
	​

(t)
	​

−1)

𝑃
𝑖
(
𝑡
)
P
i
	​

(t) = stock price on evaluation date

𝑃
𝑖
(
𝑡
−
252
)
P
i
	​

(t−252) = price 1 year (~252 trading days) ago

𝑃
𝑖
(
𝑡
−
63
)
P
i
	​

(t−63) = price 1 quarter (~63 trading days) ago

Valuation Factor (
𝑉
𝑖
V
i
	​

)

Valuation favors stocks with low P/E ratios:

𝑉
𝑖
=
NormalizeRank
(
1
𝑃
𝐸
𝑖
)
V
i
	​

=NormalizeRank(
PE
i
	​

1
	​

)

Using 
1
/
𝑃
𝐸
1/PE gives the earnings yield, so higher values indicate better value.

Quality Factor (
𝑄
𝑖
Q
i
	​

)

Quality evaluates profitability:

𝑄
𝑖
=
0.5
⋅
NormalizeRank
(
𝑅
𝑂
𝐸
𝑖
)
+
0.5
⋅
NormalizeRank
(
ProfitMargin
𝑖
)
Q
i
	​

=0.5⋅NormalizeRank(ROE
i
	​

)+0.5⋅NormalizeRank(ProfitMargin
i
	​

)

𝑅
𝑂
𝐸
𝑖
ROE
i
	​

 = Return on equity

𝑃
𝑟
𝑜
𝑓
𝑖
𝑡
𝑀
𝑎
𝑟
𝑔
𝑖
𝑛
𝑖
ProfitMargin
i
	​

 = Net profit margin

Risk / Volatility Penalty (
𝑅
𝑖
R
i
	​

)

Risk penalizes volatile stocks:

𝑅
𝑖
=
NormalizeRank
(
Volatility
𝑖
)
R
i
	​

=NormalizeRank(Volatility
i
	​

)

Volatility is calculated as the annualized standard deviation of daily returns:

Volatility
𝑖
=
std
(
daily returns
)
⋅
252
Volatility
i
	​

=std(daily returns)⋅
252
	​

Factor Normalization

All factors are normalized using rank normalization:

NormalizeRank
(
𝑋
𝑖
)
=
rank
(
𝑋
𝑖
)
−
min
⁡
(
rank
(
𝑋
)
)
max
⁡
(
rank
(
𝑋
)
)
−
min
⁡
(
rank
(
𝑋
)
)
NormalizeRank(X
i
	​

)=
max(rank(X))−min(rank(X))
rank(X
i
	​

)−min(rank(X))
	​


Best stock in a factor receives 1, worst receives 0.

For factors where lower is better (like volatility), the ranking is inverted.

Final Score

The final score combines all normalized factors:

Score
𝑖
=
NormalizeRank
(
𝑤
𝑚
𝑀
𝑖
+
𝑤
𝑣
𝑉
𝑖
+
𝑤
𝑞
𝑄
𝑖
−
𝑤
𝑟
𝑅
𝑖
)
Score
i
	​

=NormalizeRank(w
m
	​

M
i
	​

+w
v
	​

V
i
	​

+w
q
	​

Q
i
	​

−w
r
	​

R
i
	​

)

Higher scores indicate better stock picks for the selected risk profile.

Volatility reduces the score for high-risk stocks.

CLI Usage

Run backtests using:

python backtest.py


The CLI allows:

Selecting a sector from the S&P 500.

Selecting a risk profile (Conservative, Moderate, Aggressive).

Entering an evaluation date.

Optionally specifying the forward test horizon (default: 252 trading days).

The CLI outputs:

Top stock pick for the sector and date

Estimated return over the forward horizon

CSV of the full scored universe

Example
python backtest.py


CLI prompts:

Enter sector: technology
Enter risk profile: moderate
Enter date (YYYY-MM-DD): 2025-06-30


Output:

Top pick on 2025-06-30: AAPL
Return over next year: 12.35%
Full scored list saved to scored_technology_moderate.csv

Files

main.py – Factor computation and scoring

backtest.py – CLI backtesting tool

Notes

All data comes from Yahoo Finance APIs.

Momentum uses 252-day and 63-day returns.

Quality is computed using ROE and Profit Margin.

Volatility is annualized to penalize high-risk stocks.

Risk profile weights are configurable in main.py.S&P 500 Factor Model & Backtesting

This repository contains a Python system for selecting S&P 500 stocks using a factor-based ranking model and performing backtests. The model combines momentum, valuation, quality, and volatility factors with user-defined risk profiles.

Overview

The project consists of two main files:

main.py – Fetches stock data, computes factor scores, and ranks stocks.

backtest.py – Provides a command-line interface (CLI) to backtest and evaluate stock picks.

The model ranks stocks based on normalized factor scores, weighted according to the user’s risk profile.

Factor Model

The overall score for stock i is:

Score
𝑖
=
NormalizeRank
(
𝑤
𝑚
𝑀
𝑖
+
𝑤
𝑣
𝑉
𝑖
+
𝑤
𝑞
𝑄
𝑖
−
𝑤
𝑟
𝑅
𝑖
)
Score
i
	​

=NormalizeRank(w
m
	​

M
i
	​

+w
v
	​

V
i
	​

+w
q
	​

Q
i
	​

−w
r
	​

R
i
	​

)

Where:

𝑀
𝑖
M
i
	​

 = Momentum factor

𝑉
𝑖
V
i
	​

 = Valuation factor

𝑄
𝑖
Q
i
	​

 = Quality factor

𝑅
𝑖
R
i
	​

 = Risk / Volatility penalty

𝑤
𝑚
,
𝑤
𝑣
,
𝑤
𝑞
,
𝑤
𝑟
w
m
	​

,w
v
	​

,w
q
	​

,w
r
	​

 = weights defined by the selected risk profile

Momentum Factor (
𝑀
𝑖
M
i
	​

)

Momentum is a combination of long-term (1 year) and short-term (1 quarter) returns:

𝑀
𝑖
=
NormalizeRank
(
0.75
⋅
𝑃
𝑖
(
𝑡
)
𝑃
𝑖
(
𝑡
−
252
)
−
1
+
0.25
⋅
𝑃
𝑖
(
𝑡
)
𝑃
𝑖
(
𝑡
−
63
)
−
1
)
M
i
	​

=NormalizeRank(0.75⋅
P
i
	​

(t−252)
P
i
	​

(t)
	​

−1+0.25⋅
P
i
	​

(t−63)
P
i
	​

(t)
	​

−1)

𝑃
𝑖
(
𝑡
)
P
i
	​

(t) = stock price on evaluation date

𝑃
𝑖
(
𝑡
−
252
)
P
i
	​

(t−252) = price 1 year (~252 trading days) ago

𝑃
𝑖
(
𝑡
−
63
)
P
i
	​

(t−63) = price 1 quarter (~63 trading days) ago

Valuation Factor (
𝑉
𝑖
V
i
	​

)

Valuation favors stocks with low P/E ratios:

𝑉
𝑖
=
NormalizeRank
(
1
𝑃
𝐸
𝑖
)
V
i
	​

=NormalizeRank(
PE
i
	​

1
	​

)

Using 
1
/
𝑃
𝐸
1/PE gives the earnings yield, so higher values indicate better value.

Quality Factor (
𝑄
𝑖
Q
i
	​

)

Quality evaluates profitability:

𝑄
𝑖
=
0.5
⋅
NormalizeRank
(
𝑅
𝑂
𝐸
𝑖
)
+
0.5
⋅
NormalizeRank
(
ProfitMargin
𝑖
)
Q
i
	​

=0.5⋅NormalizeRank(ROE
i
	​

)+0.5⋅NormalizeRank(ProfitMargin
i
	​

)

𝑅
𝑂
𝐸
𝑖
ROE
i
	​

 = Return on equity

𝑃
𝑟
𝑜
𝑓
𝑖
𝑡
𝑀
𝑎
𝑟
𝑔
𝑖
𝑛
𝑖
ProfitMargin
i
	​

 = Net profit margin

Risk / Volatility Penalty (
𝑅
𝑖
R
i
	​

)

Risk penalizes volatile stocks:

𝑅
𝑖
=
NormalizeRank
(
Volatility
𝑖
)
R
i
	​

=NormalizeRank(Volatility
i
	​

)

Volatility is calculated as the annualized standard deviation of daily returns:

Volatility
𝑖
=
std
(
daily returns
)
⋅
252
Volatility
i
	​

=std(daily returns)⋅
252
	​

Factor Normalization

All factors are normalized using rank normalization:

NormalizeRank
(
𝑋
𝑖
)
=
rank
(
𝑋
𝑖
)
−
min
⁡
(
rank
(
𝑋
)
)
max
⁡
(
rank
(
𝑋
)
)
−
min
⁡
(
rank
(
𝑋
)
)
NormalizeRank(X
i
	​

)=
max(rank(X))−min(rank(X))
rank(X
i
	​

)−min(rank(X))
	​


Best stock in a factor receives 1, worst receives 0.

For factors where lower is better (like volatility), the ranking is inverted.

Final Score

The final score combines all normalized factors:

Score
𝑖
=
NormalizeRank
(
𝑤
𝑚
𝑀
𝑖
+
𝑤
𝑣
𝑉
𝑖
+
𝑤
𝑞
𝑄
𝑖
−
𝑤
𝑟
𝑅
𝑖
)
Score
i
	​

=NormalizeRank(w
m
	​

M
i
	​

+w
v
	​

V
i
	​

+w
q
	​

Q
i
	​

−w
r
	​

R
i
	​

)

Higher scores indicate better stock picks for the selected risk profile.

Volatility reduces the score for high-risk stocks.

CLI Usage

Run backtests using:

python backtest.py


The CLI allows:

Selecting a sector from the S&P 500.

Selecting a risk profile (Conservative, Moderate, Aggressive).

Entering an evaluation date.

Optionally specifying the forward test horizon (default: 252 trading days).

The CLI outputs:

Top stock pick for the sector and date

Estimated return over the forward horizon

CSV of the full scored universe

Example
python backtest.py


CLI prompts:

Enter sector: technology
Enter risk profile: moderate
Enter date (YYYY-MM-DD): 2025-06-30


Output:

Top pick on 2025-06-30: AAPL
Return over next year: 12.35%
Full scored list saved to scored_technology_moderate.csv

Files

main.py – Factor computation and scoring

backtest.py – CLI backtesting tool

Notes

All data comes from Yahoo Finance APIs.

Momentum uses 252-day and 63-day returns.

Quality is computed using ROE and Profit Margin.

Volatility is annualized to penalize high-risk stocks.

Risk profile weights are configurable in main.py.
