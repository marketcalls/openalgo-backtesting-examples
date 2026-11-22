# Strategies

One folder per strategy, numbered in the order tested. Each folder holds:

* `strategy.py`: the rules in code, runnable with `python strategy.py` from inside the folder.
* `README.md`: the rules in plain words, the assumptions, how to verify, the results and the verdict.
* `reports/`: the tearsheet (`tearsheet.html`), the trade list (`trades.csv`), the indicator on every candle (`signals.csv`) and every table of the run (`tables/`).

Price data always comes from Historify on the OpenAlgo server (`source="db"`). Historify stores 1-minute and daily candles; the engine builds hourly candles from the 1-minute ones. The API key is read from `../.env`.

## Log

| No. | Strategy | Market | Timeframe | Period | Capital | Closed trades | Net profit | CAGR | Max drawdown | Buy and hold | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 06 | [Momentum switch from Antonacci's dual momentum (2012), crash filter removed, 200-day EMA entry and exit filter: each quarter pick whichever of NIFTYBEES and GOLDBEES rose more, hold it only while above its 200-day EMA; 12- and 3-month lookbacks](06_niftybees_goldbees_dual_momentum_d_long/README.md) | NIFTYBEES and GOLDBEES, NSE, CNC | Daily, quarterly checks | 1 Jan 2018 to 20 Nov 2026 | Rs 10,00,000 | 27 (3-month: 34) | Rs 13,94,475.60 (3-month: Rs 26,78,505.87) | 10.33% (3-month: 15.79%) | -29.42% (3-month: -24.02%) | 14.40% a year (50:50 of the same ETFs reset quarterly), 15.92% (GOLDBEES held) | Not enough evidence: the 3-month version beats the 50:50 mix on return but not on risk, 63% of its profit is one gold trade and its neighbouring lookbacks do far worse; the 12-month baseline alone would be a Reject |
| 05 | [UT Bot (key 1, ATR 10) 60% on SBIN, RELIANCE, MAXHEALTH, CIPLA and Supertrend (10, 3) 40% on SUNPHARMA, ICICIBANK, TATASTEEL, MARUTI, one account, long only](05_two_baskets_utbot_supertrend_1h_long/README.md) | 8 NIFTY 50 stocks, NSE, CNC | 1 hour | 1 Apr 2022 to 20 Nov 2026 | Rs 10,00,000 (6 : 4 lakh) | 2,236 (UT Bot 1,809, Supertrend 427) | Rs -1,86,052.15 (UT Bot -2,62,749.81, Supertrend 76,697.66) | -4.34% | -26.63% | 14.59% a year (same 8 stocks, same 60:40) | Reject: UT Bot's hourly flips paid 5 times their gross profit in charges; Supertrend made 3.85% a year against 13.96% for holding its stocks |
| 04 | [Supertrend (10, 3) on the 10 least correlated NIFTY 50 stocks, equal allocation, long only](04_nifty50_basket_supertrend_1h_long/README.md) | 10 NIFTY 50 stocks, NSE, CNC | 1 hour | 22 Nov 2021 to 20 Nov 2026 (first trade 8 Mar 2022) | Rs 10,00,000 | 1,108 | Rs 3,25,439.77 | 5.80% | -15.70% | 12.63% a year (same 10 stocks) | Reject: steadier than 01 and survives late fills, but lags holding the same stocks by 7 points a year; charges 53% of gross |
| 03 | [NIFTYBEES 60 : GOLDBEES 40, buy and hold](03_niftybees_goldbees_60_40_buy_hold/README.md) | NIFTYBEES and GOLDBEES, NSE, CNC | Daily | 22 Nov 2021 to 20 Nov 2026 | Rs 10,00,000 | 0 (2 held) | Rs 8,43,898.38 | 13.03% | -18.88% | (itself) | Reference portfolio: the yardstick; NIFTYBEES alone made 8.55% a year, GOLDBEES alone 18.66% |
| 02 | Supertrend (10, 3) with EMA 200 filter, long only | SBIN, NSE, CNC | 1 hour | 22 Nov 2021 to 20 Nov 2026 | Rs 10,00,000 | | | | | | Pending: rerun on Historify once SBIN 1-minute history from 2020 is downloaded |
| 01 | [Supertrend (10, 3), long only](01_sbin_supertrend_1h_long/README.md) | SBIN, NSE, CNC | 1 hour | 22 Nov 2021 to 20 Nov 2026 | Rs 10,00,000 | 123 | Rs 2,65,164.78 | 4.82% | -23.03% | 127.33% | Reject: far behind buy and hold, charges took 74% of gross, fails the one-candle-late test |
