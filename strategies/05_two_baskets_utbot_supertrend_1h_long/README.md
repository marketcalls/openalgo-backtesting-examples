# Strategy 05: UT Bot (60%) and Supertrend (40%) on one Rs 10 lakh account, hourly, long only

**Verdict: Reject.** The account lost Rs 1,86,052.15 (-18.61%, -4.34% a year) over 1 April 2022 to 20 November 2026, while holding the same 8 stocks with the same 60:40 money made Rs 8,80,534.46 (+88.05%). The UT Bot half lost 43.79%: it traded 1,809 times, and charges took five times what the trades made before charges. The Supertrend half made 19.17%, against 83.31% for simply holding its four stocks.

The allocation tree is on a whiteboard: https://claude.ai/artifact/63DXqAd4Az98Stxa4ZQEsz

## The idea

Two strategies share one account. Each trades only its own money, and each buy takes an equal share of that money.

| | UT Bot | Supertrend |
|---|---|---|
| Money | 60 percent, Rs 6,00,000 | 40 percent, Rs 4,00,000 |
| Stocks | SBIN, RELIANCE, MAXHEALTH, CIPLA | SUNPHARMA, ICICIBANK, TATASTEEL, MARUTI |
| Line | ATR trailing stop, key value 1, ATR period 10 | Supertrend, ATR period 10, multiplier 3 |
| Buy | The close crosses above the trailing stop | The Supertrend turns green |
| Sell all | The close crosses below the trailing stop | The Supertrend is red at a candle's close |
| Each buy | 23.75% of the strategy's current value (about Rs 1,42,500 at the start) | 23.75% of the strategy's current value (about Rs 95,000 at the start) |

**The UT Bot** is the "UT Bot Strategy" Pine script (version 4, credited to HPotter). A trailing stop follows the close at key value x ATR (the average true range, a measure of how far the price moves in a candle). While the close stays above it, the stop only rises; while the close stays below it, the stop only falls; when the close crosses it, the stop restarts on the other side. The script's `ema(src, 1)` is the close itself, so its buy is "the close crossed above the stop" and its sell "the stop crossed above the close". The script also goes short on a sell; this version is long only, so a sell only closes the long. The Heikin Ashi option is off.

## Setup

* NSE cash market, 1-hour candles, CNC (delivery, held overnight), long only.
* Test period 1 April 2022 to 20 November 2026. Historify's 1-minute candles start on 22 November 2021; the months before April 2022 warm up the indicators, so both strategies could trade from the first day (no warm-up warning).
* Rs 10,00,000 in one account (pool "shared"): Rs 6,00,000 for the UT Bot and Rs 4,00,000 for the Supertrend. Four stocks held at once fill 95 percent of a strategy's money, and 5 percent stays in cash for a gap up.
* A market order is decided at a candle's close and fills at the next candle's open. A signal on the day's last candle is placed at 09:15 the next day. From 3 August 2026 the data has no 15:15 candle, so the 14:15 candle counts as the last.
* Zerodha charges at each trade date's rates (STT, exchange charges, SEBI fee, stamp duty, GST, DP charge), slippage 2 basis points, whole shares.
* Data from Historify (`source="db"`); benchmark NIFTY 50.
* Engine: openalgo 2.4.0, whose `bt.backtest([StrategyA, StrategyB], capital={...})` runs several strategies on one account.

## Headline figures

| | Account | UT Bot (Rs 6 lakh) | Supertrend (Rs 4 lakh) |
|---|---|---|---|
| Net profit | Rs -1,86,052.15 | Rs -2,62,749.81 | Rs 76,697.66 |
| Return | -18.61% | -43.79% | 19.17% |
| CAGR (return per year) | -4.34% | -11.68% | 3.85% |
| Max drawdown (worst fall from a peak) | -26.63% | -48.94% | -14.64% |
| Sharpe ratio (return per unit of daily swings) | -0.53 | -1.20 | 0.46 |
| Closed trades | 2,236 (5 still open) | 1,809 | 427 |
| Win rate | 32.83% | 31.23% | 39.58% |
| Average win / average loss | Rs 2,240.86 / Rs -1,241.28 | Rs 1,922.41 / Rs -1,084.62 | Rs 3,305.51 / Rs -1,996.67 |
| Profit factor (rupees won per rupee lost) | 0.88 | 0.81 | 1.08 |
| Profit of closed trades before charges | Rs 2,10,879.50 | Rs 64,379.65 | Rs 1,46,499.85 |
| Charges | Rs 4,30,926.20 | Rs 3,27,544.61 | Rs 1,03,381.59 |
| Charges as a share of that profit | 204% | 509% | 70% |
| Slippage | Rs 1,09,846.43 | Rs 84,024.40 | Rs 25,822.03 |
| Average holding | | 8.9 hourly candles (1.8 days) | 39.2 hourly candles (8.3 days) |

Year by year, the account: 2022 -12.30%, 2023 -1.93%, 2024 2.18%, 2025 -2.60%, 2026 -4.91%. The UT Bot lost money in every year; the Supertrend made a little in every year (1.20%, 5.57%, 7.20%, 3.39%, 0.64%). Their daily returns had a correlation of 0.36.

## By stock

| Stock | Strategy | Closed trades | Won | Profit after charges (Rs) | Charges (Rs) | The stock itself |
|---|---|---|---|---|---|---|
| SBIN | UT Bot | 445 | 34% | -4,422 | 83,191 | 129.3% |
| RELIANCE | UT Bot | 449 | 31% | -74,766 | 79,378 | 8.8% |
| MAXHEALTH | UT Bot | 456 | 32% | -51,445 | 81,302 | 208.2% |
| CIPLA | UT Bot | 459 | 28% | -1,32,059 | 83,616 | 39.4% |
| SUNPHARMA | Supertrend | 87 | 40% | 35,381 | 21,102 | 107.4% |
| ICICIBANK | Supertrend | 104 | 34% | 32,698 | 25,500 | 122.8% |
| TATASTEEL | Supertrend | 122 | 42% | -9,635 | 30,068 | 42.2% |
| MARUTI | Supertrend | 114 | 42% | 18,626 | 26,338 | 82.0% |

Profit includes the positions still held on 20 November 2026 (SBIN, MAXHEALTH, SUNPHARMA, ICICIBANK, MARUTI). "The stock itself" is its own price change over the test.

## Against holding

| Over the same dates | Net profit | Return | CAGR | Max drawdown | Sharpe |
|---|---|---|---|---|---|
| Strategy 05 account | Rs -1,86,052.15 | -18.61% | -4.34% | -26.63% | -0.53 |
| Same 8 stocks, same 60:40 money, bought and held | Rs 8,80,534.46 | 88.05% | 14.59% | -16.11% | 1.04 |
| UT Bot's 4 stocks held, Rs 6 lakh | Rs 5,47,286.84 | 91.21% | 15.00% | -18.82% | 0.91 |
| Supertrend's 4 stocks held, Rs 4 lakh | Rs 3,33,247.62 | 83.31% | 13.96% | -14.61% | 1.01 |
| NIFTYBEES held, Rs 10 lakh | Rs 5,15,869.65 | 51.59% | 9.38% | -14.74% | 0.83 |

NIFTY 50 rose 47.73% over the test. Each strategy's beta (how much it moved with NIFTY) was about 0.4. Holding beat both strategies, with a smaller worst fall.

## Execution stress

| | Account | UT Bot | Supertrend |
|---|---|---|---|
| Backtest (next candle's open) | Rs -1,86,052 | Rs -2,62,750 | Rs 76,698 |
| Filled at the next candle's close | Rs -2,07,110 | Rs -2,78,710 | Rs 71,600 (93% kept) |
| Every order one candle late | Rs -2,13,193 | Rs -2,91,128 | Rs 77,935 (102% kept) |

The Supertrend's small profit does not hang on the exact fill. The UT Bot loses under every fill.

## Overfitting evidence

* Nothing was tuned: both strategies run with the settings given (key value 1, ATR 10; Supertrend 10, 3), so there was no sweep, walk-forward or hold-out (stage 3) and no full robustness run (stage 4). Both failed the stage 1 and 2 gates first.
* Quick checks: the UT Bot lost money, so they are not judged. The Supertrend failed three of four: random out of sample (41% of draws kept half the Sharpe ratio, 80% needed), trade resample (70% of paths profitable, 95% needed) and variance (19% of paths profitable with 5 fewer winners in 100). Its result rests on a few trades: its best 3 trades made Rs 48,289.51, 111 percent of its closed profit.

## Warnings that matter

* **31 UT Bot buys were rejected for cash** (`margin`), the first on 4 April 2022. Each buy is 23.75 percent of the strategy's value. When the stocks already held have risen, their value is part of that figure but not of the free cash, so a fourth buy can need more than is left. The strategy kept wanting the stock and bought at a later candle. That is a small share of 1,840 entries and does not change the verdict.
* **1 UT Bot order expired unplaced** (`market_closed`), decided at 14:45 on 21 October 2025, the end of that year's Diwali Muhurat session. The 09:15 timer bought the next day.
* Charges for fills after 12 November 2026 use rates verified to that date (21 fills); the engine flags them, and the effect is a few rupees.

## How to verify

* `reports/signals.csv` has every hourly candle of the test for all 8 stocks, with the line (UT Bot stop or Supertrend), whether the close is above or below it, and each signal, worked out again from Historify's candles.
* `reports/trade_check.csv` matches the engine's trades against the rules replayed on those signals. 2,221 trades match entry and exit candle for candle. The 22 replay entries without a match are explained: 19 are buys the engine rejected for cash (it bought at a later candle), and 3 fall in special sessions whose hourly candles start off the 09:15 grid (2 March 2024, a Saturday session, and the Muhurat session of 1 November 2024).
* `reports/signal_charts.html` (from `charts.py`) draws each stock's candles with OpenAlgo Charts: the line in green and red, B and S on the signal candles, blue and orange dots at the fills, and the trade list; click a trade to zoom to it. It opens offline.

## Next steps

1. **UT Bot on daily candles, or a wider key value (2 or 3).** On hourly candles with key value 1 it flips almost twice a week per stock, and delivery charges (about 0.25 percent of the trade value per round trip) took five times its gross profit. Fewer, longer trades are the only way this rule can pay its costs. Daily candles need daily history from 2020 in Historify for the warm-up.
2. **Supertrend as a filter on holding, not as an in-and-out switch.** Its trades lagged holding the same stocks by 10 points a year. A rule that holds by default and steps aside only in a deep downtrend (a daily Supertrend, or the price below a 200-day average) keeps most of the stocks' rise and could cut the worst falls.
3. **An intraday (MIS) UT Bot on 15-minute candles.** Intraday trades pay STT on the sell only (0.025 percent) and no DP charge, a fraction of the delivery cost, and `bt.live` in sandbox mode can run only intraday strategies. Squaring off every day removes overnight gaps but also the trends that pay, so it needs its own test.

## Run

```bash
cd strategies/05_two_baskets_utbot_supertrend_1h_long
python strategy.py   # the backtest, yardsticks, reality checks, cross-check and reports
python charts.py     # the OpenAlgo Charts page, from the files strategy.py wrote
```

Use the Python that has openalgo 2.4.0 (on this machine, `D:\Quantflow 5\Day06\openalgo\.venv\Scripts\python.exe`), with the OpenAlgo server running and `OPENALGO_API_KEY` in the `.env` of `backtesting examples`. `strategy.py` takes a few minutes (it runs the account three times for the reality checks).

## Files

| File | What it is |
|---|---|
| `strategy.py` | Both strategies, the portfolio run, the yardsticks, the reality checks and the cross-check |
| `charts.py` | Builds `reports/signal_charts.html` with OpenAlgo Charts |
| `vendor/openalgo-charts-2.7.3/` | The OpenAlgo Charts browser build (Apache-2.0) with its LICENSE and NOTICE, written into the chart page |
| `reports/run_log.txt` | The printed report of the last run |
| `reports/signal_charts.html` | Candle charts with signals and fills, one stock at a time |
| `reports/strategy_report.html` | Plotly: account value and drawdown against holding, profit by stock |
| `reports/tearsheet.html` | The engine's combined tearsheet of the account |
| `reports/tearsheet_utbot.html`, `reports/tearsheet_supertrend.html` | Each strategy's own tearsheet |
| `reports/trades.csv`, `open_positions.csv`, `by_stock.csv`, `compared.csv` | Trades, positions still held, profit by stock, the comparison with holding |
| `reports/signals.csv`, `trade_check.csv` | The recomputed signals and the trade cross-check |
| `reports/tables/` | Every table of the run, the account's and each strategy's |

Not built yet: the custom per-stock tearsheet (`tearsheet.py`) that strategy 04 has, which rebuilds each stock's equity curve from the fills and checks they add up to the account.
