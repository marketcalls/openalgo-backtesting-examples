# 04 Supertrend (10, 3), hourly, long only, on the 10 least correlated NIFTY 50 stocks

**Verdict: Reject** (tested 22 Nov 2026). Spreading the Supertrend over ten stocks that move least alike made it far steadier than on SBIN alone, and it survives worse fills. But it earned 5.80 percent a year against 12.63 percent for simply holding the same ten stocks, charges took 53 percent of its profit before charges, and it lost money in 2025 and 2026.

The stocks come from [research 01](../../research/01_nifty50_low_correlation/README.md).

## The rules, as tested

| Item | Rule |
|---|---|
| Stocks | MAXHEALTH, ONGC, HINDUNILVR, ETERNAL, CIPLA, INFY, POWERGRID, BAJAJ-AUTO, KOTAKBANK, ADANIENT (NSE) |
| Timeframe | 1-hour candles |
| Indicator | Supertrend, ATR period 10, multiplier 3.0, on each stock's own candles |
| Entry | A stock's Supertrend turns green (red to green) at a candle's close and the stock is not held: buy at market, filled at the next candle's open |
| Exit | A stock's Supertrend is red at a candle's close while it is held: sell all of it at market, filled at the next candle's open |
| Last candle of the day | The order is placed at 09:15 the next trading day and fills at that open |
| Equal allocation | Each buy is 9.5 percent of the account value at that moment, in whole shares: ten stocks held at once fill 95 percent, 5 percent stays in cash |
| Direction | Long only |
| Product | CNC (delivery) |
| Capital | Rs 10,00,000 |
| Period | 22 Nov 2021 to 20 Nov 2026 |
| Data | Historify (`source="db"`): 1-minute candles, from which the engine builds the hourly ones; daily candles for the yardsticks |

## Assumptions to check

* **The first trade came on 8 Mar 2022, not in November 2021.** Historify's candles start on 22 Nov 2021, and the Supertrend needs 512 hourly candles before its value settles, so every stock waited about 3.5 months inside the run. The comparison table therefore also shows buying and holding from 8 Mar 2022. To trade from the first day, download the 10 stocks' 1-minute candles from 2021-06-01 (or earlier) in Historify and rerun.
* **Equal allocation is 9.5 percent of the account value at each buy**, not a fixed Rs 95,000 per stock: a stock's share grows or shrinks with the whole account.
* **About half the money sat in cash on average** (50 percent invested after the warm-up), because each stock is out whenever its Supertrend is red. That explains much of the low volatility.

## How to run

From this folder (needs openalgo 2.3.0 or later, plotly, and the OpenAlgo server running):

```bash
python strategy.py
```

It takes about two minutes: the backtest, two yardsticks (each from two start dates) and two reality checks.

## How to verify it yourself

1. **The indicator:** `reports/signals.csv` has every hourly candle of every stock from Historify, with its Supertrend, its colour and a note on each flip. Compare a few with Supertrend (10, 3) on the stock's 1-hour chart.
2. **A trade:** pick one in `reports/trades.csv`, then find the candle just before its `entry_time` for the same stock in `signals.csv`: it should say `turned green: BUY at next open`. The candle just before `exit_time` should be red.
3. **09:15 trades:** 100 trades have an entry or exit at 09:15: their signal came on the previous day's last candle.
4. **The automated cross-check** matched 1,105 of the 1,108 closed trades. The other 3 follow special sessions (the Diwali Muhurat session of 1 Nov 2024 and the Saturday session of 18 May 2024), where the engine builds the hourly candles from 1-minute data starting at the session's own open, while Historify's hourly view groups them differently.
5. **Charts:** `reports/custom_tearsheet.html` (Plotly: the account, each stock's equity curve and drawdown against holding it, profit by stock and year, monthly returns and a statistics table per stock), `reports/strategy_report.html` (Plotly: account value against the yardsticks) and `reports/tearsheet.html` (the engine's own report).

## Custom tearsheet

`python tearsheet.py` (after `strategy.py`) builds `reports/custom_tearsheet.html` from the saved tables in `reports/tables` and Historify's prices, without running the backtest again. Each stock's curve comes from its own fills: buys pay units x price plus charges, sales receive units x price less charges, and shares still held are valued at each day's last traded price. The ten curves add up to the engine's account value with a largest daily gap of Rs 0.00. It also writes `reports/stock_equity.csv` (each stock's Rs 1,00,000 sleeve, every day) and `reports/stock_stats.csv`.

## Results

| Figure | Value |
|---|---|
| Net profit | Rs 3,25,439.77 |
| Return / CAGR | 32.54% / 5.80% a year |
| Max drawdown | -15.70% |
| Volatility (yearly) | 8.13% |
| Sharpe ratio | 0.73 |
| Closed trades | 1,108 (37.55% won), 9 still open |
| Average win / average loss | Rs 4,911.96 / Rs -2,569.79 |
| Profit factor | 1.15 |
| Charges / slippage | Rs 3,05,254.08 / Rs 70,861.99 |

**Where the money went (closed trades):** profit before charges Rs 5,69,034.20; charges Rs 3,03,954.21 (53.4 percent of it, about Rs 274 a trade); profit after charges Rs 2,65,079.99. The rest of the net profit, about Rs 60,360, is the 9 positions still open on 20 Nov 2026. Each stock flipped about 24 times a year.

**Year by year:** 2021 0.00% (warm-up), 2022 4.69%, 2023 20.88%, 2024 9.73%, 2025 -2.44%, 2026 -2.16%.

**Compared with holding** (same Rs 10 lakh, same Historify data, orders at the next open)

| | Net profit | CAGR | Max drawdown | Volatility | Sharpe |
|---|---|---|---|---|---|
| Strategy 04 | Rs 3,25,439.77 | 5.80% | -15.70% | 8.13% | 0.73 |
| Same 10 stocks, bought and held | Rs 8,11,589.51 | 12.63% | -21.59% | 14.78% | 0.88 |
| NIFTYBEES, bought and held | Rs 5,06,517.62 | 8.55% | -15.36% | 12.38% | 0.72 |
| Same 10 stocks, held from 8 Mar 2022 | Rs 10,05,848.37 | 15.95% | -22.41% | 15.20% | 1.05 |
| NIFTYBEES, held from 8 Mar 2022 | Rs 6,24,248.11 | 10.86% | -15.12% | 12.02% | 0.92 |

**By stock** (from the custom tearsheet: every fill and charge of the stock, with shares still held at the last price; the ten add up to the account exactly). Each stock is shown as a Rs 1,00,000 sleeve, its tenth of the money.

| Stock | Profit | Sleeve return | Holding the stock from 8 Mar 2022 | Sleeve max drawdown | Closed trades | Won |
|---|---|---|---|---|---|---|
| ETERNAL | Rs 1,65,728 | +165.7% | +365.3% | -24.1% | 116 | 49% |
| ADANIENT | Rs 1,46,237 | +146.2% | +74.7% | -15.7% | 106 | 36% |
| BAJAJ-AUTO | Rs 95,926 | +95.9% | +234.2% | -18.2% | 106 | 42% |
| MAXHEALTH | Rs 69,675 | +69.7% | +216.1% | -30.8% | 107 | 36% |
| ONGC | Rs 30,571 | +30.6% | +43.5% | -20.7% | 105 | 44% |
| HINDUNILVR | Rs 4,431 | +4.4% | +7.2% | -29.8% | 103 | 36% |
| CIPLA | Rs -42,966 | -43.0% | +45.1% | -55.6% | 107 | 35% |
| POWERGRID | Rs -43,382 | -43.4% | +71.8% | -62.0% | 120 | 32% |
| KOTAKBANK | Rs -48,213 | -48.2% | +48.9% | -81.2% | 115 | 32% |
| INFY | Rs -52,566 | -52.6% | -35.6% | -67.5% | 123 | 36% |

Only ADANIENT did better under the strategy than simply held. On the other nine, holding the stock beat trading it, and on CIPLA, POWERGRID and KOTAKBANK the strategy lost money on stocks that rose. (The `by_stock.csv` that `strategy.py` writes differs by a few hundred rupees per stock, because the engine's open profit leaves out the buy charges of positions still held; the tearsheet's figures include them.)

**Reality checks**

| Test | Net profit | Kept |
|---|---|---|
| Filled at the next candle's close | Rs 2,86,326.30 | 88% |
| Every order one candle late | Rs 2,57,377.69 | 79% |

**Overfitting quick checks:** 3 failed (random out of sample 63 percent against the 80 percent rule; trade resample 91.5 percent of paths profitable against 95; variance 17 percent profitable with 5 fewer winners in 100), 1 informational.

## Verdict: Reject

* **It lost to holding the same stocks:** 5.80 against 12.63 percent a year, and 15.95 percent when holding also starts on 8 Mar 2022. Its Sharpe ratio (0.73) is lower too, so it was not a better trade-off of risk for return either.
* **Charges ate more than half the profit** before charges: about 24 flips per stock per year, each a delivery round trip.
* **It lost money in 2025 and 2026,** and three quick overfitting checks failed: the profit leans on a few trends (ETERNAL, ADANIENT, BAJAJ-AUTO).

**What did work:** diversification did its job. Against Supertrend on SBIN alone (strategy 01), the worst fall dropped to 15.70 percent, the yearly swings to 8.13 percent, and a one-candle delay now keeps 79 percent of the profit instead of wiping most of it out. The weak part is the hourly Supertrend itself, not the basket.

## What to try next

1. **Hold the basket and use Supertrend only to step aside:** stay invested in all ten while the daily trend is up and move a stock to cash only on a daily red flip. Far fewer trades, so far less STT.
2. **The same rules on daily candles.** Needs about two years of warm-up (512 daily candles), so download the ten stocks' daily candles from 2019 in Historify first.
3. **Rebalance the held basket every year** (equal weight) and compare it with buying once: research 01 suggests the stocks drift apart in weight.
