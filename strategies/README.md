# Strategies

One folder per strategy, numbered in the order tested. Each folder holds:

* `strategy.py`: the rules in code, runnable with `python strategy.py` from inside the folder.
* `README.md`: the rules in plain words, the assumptions, how to verify, the results and the verdict.
* `reports/`: the tearsheet (`tearsheet.html`), the trade list (`trades.csv`), the indicator on every candle (`signals.csv`) and every table of the run (`tables/`).

Price data always comes from Historify on the OpenAlgo server (`source="db"`). Historify stores 1-minute and daily candles; the engine builds hourly candles from the 1-minute ones. The API key is read from `../.env`.

## Log

| No. | Strategy | Market | Timeframe | Period | Capital | Closed trades | Net profit | CAGR | Max drawdown | Buy and hold | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 04 | [Supertrend (10, 3) on the 10 least correlated NIFTY 50 stocks, equal allocation, long only](04_nifty50_basket_supertrend_1h_long/README.md) | 10 NIFTY 50 stocks, NSE, CNC | 1 hour | 22 Nov 2021 to 20 Nov 2026 (first trade 8 Mar 2022) | Rs 10,00,000 | 1,108 | Rs 3,25,439.77 | 5.80% | -15.70% | 12.63% a year (same 10 stocks) | Reject: steadier than 01 and survives late fills, but lags holding the same stocks by 7 points a year; charges 53% of gross |
| 03 | [NIFTYBEES 60 : GOLDBEES 40, buy and hold](03_niftybees_goldbees_60_40_buy_hold/README.md) | NIFTYBEES and GOLDBEES, NSE, CNC | Daily | 22 Nov 2021 to 20 Nov 2026 | Rs 10,00,000 | 0 (2 held) | Rs 8,43,898.38 | 13.03% | -18.88% | (itself) | Reference portfolio: the yardstick; NIFTYBEES alone made 8.55% a year, GOLDBEES alone 18.66% |
| 02 | Supertrend (10, 3) with EMA 200 filter, long only | SBIN, NSE, CNC | 1 hour | 22 Nov 2021 to 20 Nov 2026 | Rs 10,00,000 | | | | | | Pending: rerun on Historify once SBIN 1-minute history from 2020 is downloaded |
| 01 | [Supertrend (10, 3), long only](01_sbin_supertrend_1h_long/README.md) | SBIN, NSE, CNC | 1 hour | 22 Nov 2021 to 20 Nov 2026 | Rs 10,00,000 | 123 | Rs 2,65,164.78 | 4.82% | -23.03% | 127.33% | Reject: far behind buy and hold, charges took 74% of gross, fails the one-candle-late test |
