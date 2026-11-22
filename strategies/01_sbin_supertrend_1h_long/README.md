# 01 SBIN Supertrend (10, 3), hourly, long only

**Verdict: Reject** (tested 22 Nov 2026). It made money, but much less than simply holding SBIN, charges took three quarters of the gross profit, and the profit halved when orders were one candle late.

## The rules, as tested

| Item | Rule |
|---|---|
| Instrument | SBIN, NSE cash market |
| Timeframe | 1-hour candles (09:15, 10:15, ... the last candle of the day) |
| Indicator | Supertrend, ATR period 10, multiplier 3.0 |
| Entry | The Supertrend turns green (red to green) at a candle's close and no shares are held: BUY at market, filled at the open of the next candle |
| Exit | The Supertrend is red at a candle's close while shares are held: SELL ALL at market, filled at the open of the next candle |
| Last candle of the day | A signal at the close of the day's last candle is placed at 09:15 the next trading day and fills at that open |
| Direction | Long only, never short |
| Stop-loss, target | None: the red flip is the exit |
| Product | CNC (delivery), held overnight |
| Capital | Rs 10,00,000 |
| Size | 95 percent of the account value on each buy, whole shares (grows or shrinks with the account) |
| Costs | Indian delivery charges at each trade date's rates, slippage 2 basis points per fill |
| Period | 22 Nov 2021 to 20 Nov 2026 (5 years); candles from May 2021 warm up the indicator |

## Assumptions to check

* **"Supertrend 3,0"** is read as ATR period 10 (the usual default) with multiplier 3.0. If you meant other values, change `period` and `multiplier` in `strategy.py`.
* **Delivery, not intraday.** On hourly candles the engine would otherwise trade MIS and close every position by 15:00. CNC lets a trend run for days.
* **Entry only on a flip.** If the Supertrend is already green on the first day of the test, the strategy waits for the next red-to-green flip.
* **Market orders at the next candle's open**, as you specified. A signal on the day's last candle fills at the next day's 09:15 open (the engine refuses an order that can only fill after the market has closed).
* **Data quirks:** three Diwali Muhurat sessions (2024, 2025, 2026) are left out because their candles do not start on the hourly grid. Since 3 Aug 2026 the broker's data has no 15:15 candle; the 14:15 candle is the last of the day.

## How to run

From the `backtesting examples` folder:

```bash
pip install -U openalgo                     # the backtesting engine needs openalgo 2.3.0 or later
python data/download_history.py --symbol SBIN --exchange NSE --interval 1h --years 5   # already done: data/SBIN_NSE_1h.csv
cd strategies/01_sbin_supertrend_1h_long
python strategy.py
```

`strategy.py` reads the saved CSV, so it needs no API key and no server once the data is downloaded.

## How to verify it yourself

1. **The indicator.** Open `reports/signals.csv`: every hourly candle from 22 Nov 2021 with its Supertrend value, its colour and a note on each flip. Compare a few candles with Supertrend (10, 3) on SBIN's 1-hour chart in your charting platform. Small differences are possible if the platform works out the ATR differently.
2. **An entry.** Pick a trade in `reports/trades.csv` and find its `entry_time` in `signals.csv`. The candle just before it should say `turned green: BUY at next open`, and the `entry_price` should be that candle's open plus about 0.02 percent (slippage).
3. **An exit.** The candle just before `exit_time` should be the first red candle after the entry.
4. **09:15 trades.** An entry or exit at 09:15 means the signal came on the previous day's last candle (2 entries and 4 exits).
5. **Charges.** `reports/tables/costs.csv` has one row per fill with every charge.
6. **The full report.** Open `reports/tearsheet.html` in a browser.

An automated cross-check (the Supertrend worked out again from the raw candles) matched all 123 closed trades: every entry was at the open after a green flip, and every exit at the open after a red candle.

## Results

22 Nov 2021 to 20 Nov 2026, Rs 10,00,000.

| | Strategy | Buy and hold SBIN |
|---|---|---|
| Net profit | Rs 2,65,164.78 | Rs 12,73,298.78 |
| Return | 26.52% | 127.33% |
| CAGR (yearly growth) | 4.82% | 17.87% |
| Max drawdown (worst fall from a peak) | -23.03% | -24.56% |
| Sharpe ratio | 0.36 | |
| Closed trades | 123 (1 still open) | |
| Win rate | 34.15% | |
| Average win / average loss | Rs 46,169.98 / Rs -22,664.77 | |
| Profit factor (rupees won per rupee lost) | 1.06 | |
| Time in the market | 54.49% | 100% |

**Where the money went (closed trades):**

* Profit before charges: Rs 3,97,376.40.
* Charges: Rs 2,94,083.42, of which STT about Rs 2.63 lakh. That is 74 percent of the gross profit, about Rs 2,391 per round trip (0.25 percent of the trade value).
* Profit after charges: Rs 1,03,292.98. The rest of the net profit, about Rs 1.62 lakh, is the position still open on 20 Nov 2026, valued at that day's close.
* Slippage (already inside the prices): Rs 65,106.35.
* The 5 best trades made Rs 7,19,055.17 together, more than the whole net profit: many small losses, paid for by a few long trends.

**Year by year:** 2021 (Dec only) -3.78%, 2022 17.95%, 2023 0.08%, 2024 3.15%, 2025 5.32%, 2026 2.54%. Almost all the gain came in 2022.

**Reality checks:**

| Test | Net profit | Kept |
|---|---|---|
| Filled at the next candle's close instead of its open | Rs 2,12,603.05 | 80% |
| Every order one candle late | Rs 1,08,758.54 | 41% |

**Overfitting quick checks:** 3 failed (random out of sample, trade resample, variance), 1 informational. The result depends heavily on which trades and days you count.

## Verdict: Reject

* It lost to buy and hold by a wide margin (4.82 percent a year against 17.87 percent) with almost the same worst fall.
* Its CAGR is below a fixed deposit.
* Hourly flips trade too often for delivery: STT alone took about two thirds of the gross profit.
* One candle of delay removed 59 percent of the profit, below the 50 percent kept that a tradable edge should survive.

The backtest did its job: it showed this rule is not worth trading before any money was at risk.

## What to try next

1. **The same rule on daily candles.** Far fewer flips, so far fewer charges; whipsaws on the hourly chart are the main cost.
2. **A higher-timeframe filter.** Take hourly green flips only while the daily Supertrend (or a 200-day average) is also up, to skip counter-trend trades.
3. **Wider bands.** Test a larger multiplier (for example 4 or 5) to cut the number of flips, and check it with walk-forward rather than picking the best value from one run.
