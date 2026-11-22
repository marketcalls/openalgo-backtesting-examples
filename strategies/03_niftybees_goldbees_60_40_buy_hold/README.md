# 03 NIFTYBEES and GOLDBEES, 60:40, buy and hold

**Verdict: Reference portfolio** (tested 22 Nov 2026). A passive mix has no trading rules to validate; it is the yardstick the other strategies should beat. It grew Rs 10 lakh to Rs 18.44 lakh in five years (13.03 percent a year) with a worst fall of 18.88 percent, far ahead of strategies 01 and 02.

## The rules, as tested

| Item | Rule |
|---|---|
| Instruments | NIFTYBEES (NIFTY 50 ETF) and GOLDBEES (gold ETF), NSE |
| Timeframe | Daily candles |
| Entry | On the first day (22 Nov 2021), at its close, place market buy orders for 60 percent (NIFTYBEES) and 40 percent (GOLDBEES) of 95 percent of the account, in whole units. They fill at the next day's open (23 Nov 2021) |
| Cash | 5 percent kept in cash, as in strategies 01 and 02, so a higher open does not leave an order short of money |
| Exit | None: both are held to the end and valued at the last close |
| Rebalance | None: the weights drift with prices |
| Product | CNC (delivery) |
| Capital | Rs 10,00,000 |
| Period | 22 Nov 2021 to 20 Nov 2026 (5 years) |
| Data | Historify, daily candles (`source="db"`) |

## Assumptions to check

* **The day-one open was a poor price for NIFTYBEES.** ETF opening prices can carry stray trades: on 23 Nov 2021 NIFTYBEES opened at 193.40, between closes of 188.53 (the day before) and 189.40 (that day), and traded as low as 177.20. The buy at 193.45 (open plus slippage) cost about 2 percent more than that day's close. This is the rule you chose (fill at the next open); the same 3,023 units bought at that day's close would have cost about Rs 12,000 less.
* **Charges are slightly overstated.** The engine charges ETF units like shares: 0.1 percent STT on the buy (about Rs 964 here). Under the STT rules, equity ETF units pay STT only when sold (0.001 percent) and gold ETFs pay none. The engine also assumes a tick of 0.05 for both ETFs, so slippage is a little higher than real.
* **No sale at the end.** The holdings are valued at the last close; selling them would add small charges (and capital gains tax, which no backtest here includes).
* **"60:40" is the split at purchase.** It is not kept: by the end gold's rise had moved it to about 49:51.

## How to run

From this folder (needs openalgo 2.3.0 or later and the OpenAlgo server running):

```bash
python strategy.py
```

## How to verify it yourself

1. **What was bought:** `reports/holdings.csv` gives the units, buy price, cost and value now of each ETF.
2. **The prices:** `reports/prices.csv` has each day's close of both ETFs from Historify; `reports/tables/fills.csv` shows each buy's price. The buy prices are the 23 Nov 2021 opens (193.40 and 42.06) plus slippage, rounded to the 0.05 tick: 193.45 and 42.15.
3. **The end value by hand:** 3,023 x 294.22 = Rs 8,89,427.06 (NIFTYBEES) and 8,998 x 102.21 = Rs 9,19,685.58 (GOLDBEES), plus Rs 34,785.74 cash = Rs 18,43,898.38, the end value below.
4. **The cash:** Rs 10,00,000 less Rs 5,84,799.35 and Rs 3,79,265.70 (the two purchases) less Rs 1,149.21 charges = Rs 34,785.74.
5. **The full report:** open `reports/tearsheet.html` in a browser.

## Results

| Figure | Value |
|---|---|
| Start value | Rs 10,00,000.00 |
| End value | Rs 18,43,898.38 |
| Net profit | Rs 8,43,898.38 |
| Total return | 84.39% |
| CAGR (yearly growth) | 13.03% |
| Volatility (yearly) | 12.00% |
| Sharpe ratio | 1.08 |
| Sortino ratio | 1.53 |
| Calmar ratio (CAGR / worst fall) | 0.69 |
| Max drawdown | -18.88% (Rs 4,19,619.44), from the high of 29 Jan 2026 to the low of 23 Mar 2026; not yet recovered |
| Below its highest value on 20 Nov 2026 | 17.02% |
| Longest time below a previous high | 295 days (still going) |
| Best / worst year | 35.96% (2025) / -3.88% (2026 to date) |
| Best / worst month | 8.50% / -9.13% |
| Best / worst day | 4.65% / -6.33% |
| Days up | 55.92% |
| Charges / slippage | Rs 1,149.21 / Rs 960.97 |

**Holdings**

| ETF | Units | Buy price | Cost | Last close | Value now | Return | Weight at start | Weight now |
|---|---|---|---|---|---|---|---|---|
| NIFTYBEES | 3,023 | 193.45 | Rs 5,84,799.35 | 294.22 | Rs 8,89,427.06 | 52.09% | 60.7% | 49.2% |
| GOLDBEES | 8,998 | 42.15 | Rs 3,79,265.70 | 102.21 | Rs 9,19,685.58 | 142.49% | 39.3% | 50.8% |

Cash not invested: Rs 34,785.74.

**The same Rs 10 lakh held other ways** (same rules: next-day open, 5 percent cash)

| | Net profit | CAGR | Volatility | Max drawdown | Sharpe |
|---|---|---|---|---|---|
| 60:40, bought once (this strategy) | Rs 8,43,898.38 | 13.03% | 12.00% | -18.88% | 1.08 |
| 60:40, rebalanced every year | Rs 8,28,609.28 | 12.84% | 10.85% | -16.70% | 1.16 |
| NIFTYBEES only | Rs 5,06,517.62 | 8.55% | 12.38% | -15.36% | 0.72 |
| GOLDBEES only | Rs 13,49,920.15 | 18.66% | 17.88% | -29.79% | 1.04 |

**Year by year**

| Year | 60:40 | NIFTYBEES | GOLDBEES |
|---|---|---|---|
| 2021 (23 Nov to 31 Dec) | -2.43% | -2.97% | -1.62% |
| 2022 | 8.07% | 5.32% | 12.14% |
| 2023 | 17.79% | 20.51% | 14.01% |
| 2024 | 13.60% | 10.15% | 18.65% |
| 2025 | 35.96% | 11.45% | 69.37% |
| 2026 (to 20 Nov) | -3.88% | -0.36% | -7.03% |

The daily returns of the two ETFs had a correlation of 0.09: on most days they moved independently of each other. That is why the mix is steadier than either part.

## What it shows

* **Diversification worked.** The mix earned more than NIFTYBEES alone (13.03 against 8.55 percent a year) with far less of a fall than GOLDBEES alone (19 against 30 percent).
* **Gold carried these five years.** GOLDBEES rose 142 percent, most of it in 2025 (69 percent). The result leans on that one year; a period without a gold rally would look different.
* **A yearly rebalance made it steadier** at almost the same return: lower volatility (10.85 against 12.00 percent), a smaller worst fall (16.70 against 18.88 percent) and a better Sharpe ratio (1.16 against 1.08), because it sold some gold after its run-up.
* **Against strategies 01 and 02:** this passive mix beat both SBIN Supertrend strategies by a wide margin with a smaller worst fall. Any trading strategy here should be judged against it.

## What to try next

1. **Rebalance on a schedule** (every year or quarter) as the main version, since it held the risk lower.
2. **Other splits**, such as 70:30 or 50:50, with the same data (`params={"nifty_pct": 70}`).
3. **A longer history** (download more years of daily candles in Historify) to see the mix through a period without a gold rally.
