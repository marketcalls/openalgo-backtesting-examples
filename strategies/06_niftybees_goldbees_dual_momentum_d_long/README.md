# Strategy 06: Momentum switch between NIFTYBEES and GOLDBEES, with a 200-day EMA filter

This started as Antonacci's dual momentum. It was tested first with the paper's crash filter, then without it, and then with a 200-day EMA entry and exit filter.

**Verdict: Not enough evidence.**

**The 3-month version is the one that worked:** each quarter it picks the ETF that rose more over 3 months, and holds it only while the daily close is above its 200-day EMA.
* **Return and risk:** 15.79% a year, a worst fall of 24.02%, and a Sharpe ratio of 1.03.
* **Trades:** 34 closed, just over the 30 the persona asks for.
* **Execution:** it keeps its profit with worse fills.

**Why that is not yet enough:**
* **Against holding:** it only matches holding GOLDBEES (15.92% a year). It is less steady than a 50:50 mix of the same two ETFs, which made 14.40% a year with a worst fall of 19.53% and a Sharpe ratio of 1.29.
* **One trade:** a single gold trade made 63% of its profit.
* **Its neighbours:** they do much worse (6-month lookback 11.30%, 12-month 10.33%).
* **Overfitting check:** one of the engine's quick overfitting checks failed.

**The 12-month baseline would be a Reject:** with the EMA filter it made 10.33% a year, less than holding either ETF.

**What would settle it:** the same rules, unchanged, on a longer history, and a walk-forward test of the lookback.

Whiteboard with the idea, the plan and the results: https://claude.ai/artifact/LhAHCEb495p5CokEDFqE8U (private until shared).

## How the rules got here

1. **Antonacci's dual momentum** (*Risk Premia Harvesting Through Dual Momentum*, first version April 2012, revised January 2013) is Faber's relative strength plus a crash filter.
   * Pick the asset that rose more over the lookback.
   * Hold it only if that rise beat the safe return (T-bills in the paper); otherwise hold the safe asset.
   * The paper tested four pairs of US asset classes with monthly checks and a 12-month lookback, 1974 to 2011, without costs. Dual momentum on US against foreign stocks made 15.79% a year with a worst fall of 23.01%, against 11.49% and 50.65% for holding US stocks (Table 1).
2. **Applied here** to one pair, NIFTYBEES against GOLDBEES (the paper never paired stocks with gold), checked every quarter, with an FD-like 6% a year as the safe return.
3. **Crash filter removed** at the user's request because it did more harm than good. On the 12-month lookback it never acted (one ETF always beat 6%). On the 3-month lookback it cut the return from 11.83% to 9.26% a year.
4. **200-day EMA filter added** at the user's request: no buy while the daily close is below the 200-day EMA, and a sale when a held ETF closes below it.

## Rules as tested

| Part | Rule |
|---|---|
| Market | NIFTYBEES and GOLDBEES, NSE cash market, daily candles, CNC (delivery) |
| Check | Every quarter: the decision uses the close of the first session of January, April, July and October (`self.every("quarter")`); orders fill at the next session's open |
| Momentum | Each ETF's return over the lookback, `ta.roc` on daily closes: 12 months = 247 sessions, 3 months = 62 sessions (NSE averaged 247 sessions a year from 2015 to 2025) |
| Pick | The ETF with the higher return |
| EMA filter, entry | No buy while the pick's daily close is below its 200-day EMA. The strategy waits in cash, looks at every day's close, and buys at the next open after the first close above the EMA, unless the next quarterly check picks the other ETF |
| EMA filter, exit | While holding, a daily close below the 200-day EMA sells at the next open; then it waits in cash as above |
| Switch | When the pick changes, the old ETF is sold at the next open and the new one bought at the following open, once the sale money is in the account (and only if it is above its EMA) |
| Sizing | 95% of the account in the chosen ETF; 5% cash buffer because ETF opening prices can be stray |

**The EMA itself:**
* It is `openalgo.ta.ema(close, 200)`, worked out on every Historify daily candle from 22 Nov 2016, as a chart draws it.
* The engine's own `self.I` EMA would have waited for 2,048 bars (8.3 years) of history before its first decision.
* From 1 Jan 2018, this EMA is within 0.16% of one started in 2008. The price is never on the other side of one and not the other.

## Setup

* **Period:** 1 Jan 2018 to 20 Nov 2026, 36 quarterly checks. Historify's daily candles start on 22 Nov 2016, and the 12-month lookback needs the first year. Historify has no GOLDBEES candle on 7 May 2019.
* **Capital:** Rs 10,00,000.
* **Costs:** the zerodha preset for delivery.
  * The engine's dated rates start on 1 Jul 2020, so earlier trades are charged at the 1 Jul 2020 rates (`CostModel(backfill=True)`). Delivery STT was 0.1% on both sides then too.
  * The engine charges ETFs like shares (0.1% STT), which overstates their real STT.
* **Slippage:** 2 basis points. **Fills:** the next open.
* **Benchmark:** the NIFTY 50 index from Historify: 148.08% over the test, 10.73% a year, worst fall 38.44% (a price index: no dividends, no charges).

## Headline figures

| | 12-month lookback (baseline) | 3-month lookback |
|---|---|---|
| Net profit | Rs 13,94,475.60 | Rs 26,78,505.87 |
| Return | 139.45% | 267.85% |
| CAGR | 10.33% | 15.79% |
| Max drawdown | -29.42% (18 Oct 2021 to 3 Nov 2022) | -24.02% (29 Jan to 23 Mar 2026) |
| Volatility (yearly) | 16.82% | 15.44% |
| Sharpe ratio | 0.67 | 1.03 |
| Closed trades | 27 | 34 |
| Trades a year | 3.04 | 3.83 |
| Win rate | 29.63% | 41.18% |
| Days in NIFTYBEES / GOLDBEES / cash | 42.10% / 47.82% / 10.08% | 45.96% / 46.64% / 7.40% |
| Charges | Rs 66,153.25 (4.53% of gross) | Rs 1,36,862.78 (4.86% of gross) |
| Beta to NIFTY | 0.28 | 0.28 |
| FD interest the cash days would have earned (estimate) | Rs 65,593 | Rs 85,393 |
| Engine's quick overfitting checks | too few trades to judge | 2 passed, 1 failed (random out-of-sample), 1 informational |

Both versions are in cash at the end of the test: GOLDBEES closed below its 200-day EMA on 21 Oct 2026 and was sold on 22 Oct.

**Year by year, 12-month:** 2018 -7.05%, 2019 -1.87%, 2020 25.79%, 2021 16.76%, 2022 -20.42%, 2023 18.85%, 2024 6.67%, 2025 67.01%, 2026 6.09%.

**Year by year, 3-month:** 2018 -13.47%, 2019 14.94%, 2020 35.79%, 2021 25.10%, 2022 8.06%, 2023 17.42%, 2024 0.66%, 2025 67.01%, 2026 2.08%.

**What the EMA filter did:**
* **The exit is what matters.** As an entry filter only, it changed almost nothing: 12.42% a year for the 12-month version (the same as no filter) and 11.92% for the 3-month version.
* **It saved the 3-month version from the 2020 crash.** NIFTYBEES closed below its EMA in late February 2020, so the strategy sold on 28 Feb at 121.60 instead of holding to the April check. That trade lost 6.1% instead of 30.5%. The strategy then bought gold on 3 Apr 2020.
* **It cut the 2026 gold fall short.** Both versions sold GOLDBEES on 22 Oct 2026 at 117.10.
* **It whipsawed when prices hovered around the EMA.** From July to November 2022 the 12-month version bought and sold GOLDBEES nine times around its EMA, losing Rs 3,34,089 together (Rs 1,63,374 of it on one stray opening price, below). The 3-month version had 5 short NIFTYBEES trades in July and August 2026 that lost Rs 42,148.
* **Charges rose** to Rs 66,153 and Rs 1,36,863, still under 5% of gross profit.
* **One stray opening price cost the 12-month version Rs 1.63 lakh.** On 27 Oct 2022 the EMA exit sold GOLDBEES at the open at 37.55, when it had closed at 43.17 the day before and 43.46 that day. That one fill lost 14.4%.

## 3-month against 12-month returns

With the EMA filter, the 3-month lookback made 5.46 points a year more than the 12-month one, and its worst fall was smaller.

These are every 3- and 12-month stretch of the test (rolling returns, after charges):

| Window | Portfolio | Average | Median | Worst | Best | Positive | Above FD |
|---|---|---|---|---|---|---|---|
| 3 months | With EMA filter, 12-month | 3.0% | 2.0% | -22.2% | 45.4% | 61.0% | 52.7% |
| 3 months | With EMA filter, 3-month | 4.1% | 3.1% | -16.7% | 45.4% | 67.1% | 58.6% |
| 3 months | No EMA filter, 12-month | 3.8% | 3.2% | -20.3% | 45.4% | 64.6% | 58.1% |
| 3 months | No EMA filter, 3-month | 3.8% | 3.4% | -32.1% | 45.4% | 67.7% | 59.7% |
| 3 months | NIFTYBEES held | 3.1% | 3.4% | -34.3% | 30.9% | 66.9% | 60.7% |
| 3 months | GOLDBEES held | 4.5% | 3.3% | -20.5% | 46.0% | 70.9% | 61.9% |
| 3 months | 60:40 held | 3.6% | 3.7% | -18.6% | 25.1% | 77.9% | 69.0% |
| 12 months | With EMA filter, 12-month | 14.2% | 14.7% | -27.6% | 111.7% | 70.4% | 66.0% |
| 12 months | With EMA filter, 3-month | 21.1% | 16.7% | -17.4% | 111.7% | 89.6% | 80.5% |
| 12 months | No EMA filter, 12-month | 17.6% | 14.4% | -16.8% | 111.7% | 84.6% | 69.5% |
| 12 months | No EMA filter, 3-month | 18.9% | 15.0% | -23.6% | 111.7% | 84.4% | 74.9% |
| 12 months | NIFTYBEES held | 12.9% | 9.8% | -29.1% | 84.2% | 82.8% | 64.5% |
| 12 months | GOLDBEES held | 21.7% | 18.0% | -17.5% | 113.8% | 90.4% | 79.8% |
| 12 months | 60:40 held | 16.0% | 16.1% | -9.0% | 53.4% | 98.8% | 87.9% |

* **"Above FD"** is the share of stretches that beat 6% a year (1.47% for 3 months).
* **The 3-month version with the EMA** had the highest average 12-month return (21.1%). Its worst 12 months lost 17.4%.
* **Holding 60:40** was the steadiest: positive in 98.8% of 12-month stretches, with a worst of -9.0%.

## Against holding, the variants and the filters

| Portfolio | Net profit (Rs) | CAGR | Max drawdown | Volatility | Sharpe | Closed trades | Days in cash |
|---|---|---|---|---|---|---|---|
| **With EMA filter, 12-month (baseline)** | 13,94,476 | 10.33% | -29.42% | 16.82% | 0.67 | 27 | 10.1% |
| **With EMA filter, 3-month** | 26,78,506 | 15.79% | -24.02% | 15.44% | 1.03 | 34 | 7.4% |
| No EMA filter, 12-month | 18,28,813 | 12.42% | -29.72% | 16.68% | 0.78 | 7 | 0.4% |
| No EMA filter, 3-month | 17,00,989 | 11.83% | -36.89% | 16.85% | 0.75 | 17 | 0.8% |
| EMA for entries only, 12-month | 18,28,813 | 12.42% | -29.72% | 16.68% | 0.78 | 7 | 0.4% |
| EMA for entries only, 3-month | 17,19,486 | 11.92% | -36.46% | 16.84% | 0.75 | 17 | 0.9% |
| With EMA filter, 6-month | 15,89,840 | 11.30% | -32.70% | 16.83% | 0.72 | 31 | 7.4% |
| With EMA filter, 9-month | 21,24,386 | 13.68% | -29.59% | 17.39% | 0.82 | 27 | 6.9% |
| With EMA filter, 12-month, checked monthly | 10,76,001 | 8.57% | -27.25% | 17.21% | 0.56 | 34 | 7.6% |
| With EMA filter, 3-month, checked monthly | 21,97,911 | 13.98% | -26.07% | 15.79% | 0.91 | 39 | 7.2% |
| Crash filter (6% FD), no EMA, 12-month | 18,28,813 | 12.42% | -29.72% | 16.68% | 0.78 | 7 | 0.4% |
| Crash filter (6% FD), no EMA, 3-month | 11,96,280 | 9.26% | -36.83% | 16.58% | 0.62 | 18 | 9.2% |
| Crash filter at 0%, no EMA, 3-month | 18,21,574 | 12.38% | -36.89% | 16.78% | 0.78 | 17 | 3.6% |
| Crash filter only, 12-month | 6,76,201 | 5.99% | -20.17% | 9.92% | 0.64 | 9 | 0.0% |
| Crash filter only, 3-month | 7,62,789 | 6.59% | -23.64% | 9.68% | 0.71 | 19 | 8.5% |
| NIFTYBEES held | 16,39,398 | 11.54% | -34.92% | 14.46% | 0.83 | 0 | 0.0% |
| GOLDBEES held | 27,16,271 | 15.92% | -29.99% | 16.23% | 0.99 | 0 | 0.0% |
| 60:40 held (strategy 03 mix) | 20,70,079 | 13.46% | -21.68% | 11.40% | 1.16 | 0 | 0.0% |
| 50:50 reset every quarter | 23,03,562 | 14.40% | -19.53% | 10.87% | 1.29 | 0 | 0.0% |
| NIFTY 50 index (benchmark) | | 10.73% | -38.44% | 16.66% | | | |

What the table says:

* **The EMA filter helped the 3-month version and hurt the 12-month one.** It took the 3-month version from 11.83% to 15.79% a year and its worst fall from 36.89% to 24.02%. It took the 12-month version from 12.42% to 10.33%.
* **The lookback still decides the outcome.** With the filter, 3, 6, 9 and 12 months give 15.79%, 11.30%, 13.68% and 10.33% a year. Checked monthly instead, the 12-month and 3-month versions give 8.57% and 13.98%. The 3-month result stands out from its neighbours instead of sitting on a plateau.
* **The fixed mix is still the steadiest.** 50:50 reset quarterly has the best Sharpe ratio (1.29) and the smallest worst fall (-19.53%). The 3-month version with the EMA beats it on return by 1.39 points a year and matches GOLDBEES held, but with more risk than the mix.
* **The crash filter rows** show why it was removed: identical to no filter on 12 months, and 2.57 points a year worse on 3 months. A hurdle of 0% gives 12.38%, within the noise of no filter. The filter alone halved volatility but made only about 6% a year.

## Execution stress

| Run | Net profit | Kept |
|---|---|---|
| 12-month, filled at the next close | Rs 17,39,371 | 125% |
| 12-month, every order one day late | Rs 19,41,141 | 139% |
| 3-month, filled at the next close | Rs 24,87,085 | 93% |
| 3-month, every order one day late | Rs 28,55,866 | 107% |

* **Both versions keep their profit with worse fills.**
* **The 12-month version does better with them,** partly because it then avoids the stray 27 Oct 2022 open.

## Overfitting and red flags

* **Trade count:** 27 closed trades (12-month) and 34 (3-month), around the 30 needed before any check can tell skill from luck.
* **Profit from a few calls:**
  * In the 3-month version, the best 3 trades made 101% of the profit, and the GOLDBEES trade from January 2025 to July 2026 alone made Rs 16,85,322 (63%).
  * In the 12-month version, the best 3 made 109%.
* **A rule added after seeing results:** the EMA filter was added after the first results were known. It helps one lookback and hurts the other, so its benefit may be specific to this history.
* **A lone good setting:** the 3-month result is well above the 6-month (11.30%) and 12-month (10.33%) results with the same filter.
* **The engine's quick checks** on the 3-month version: 2 passed, 1 failed (random out-of-sample), 1 informational.

## Stray opening prices

Daily ETF opens can trade far from the fund's value:
* **How many:** 22 fills in the 12-month version and 15 in the 3-month version were more than 0.5% outside the closes on either side.
* **Net effect:** they cost the 12-month version Rs 1,46,627, and saved the 3-month version Rs 29,456.
* **The worst one:** the GOLDBEES sale at 37.55 on 27 Oct 2022.

With an EMA exit, the strategy sells more often at the open, so this risk matters more than it did before. A real version should place its orders after the first few minutes, or as limit orders near the ETF's live fund value. Details are in `reports/stray_opens.csv`.

## Warnings that matter

* **Charges before July 2020** are charged at the July 2020 rates (backfill).
* **2018 has no holiday list** in the engine (the server's holiday tables start in 2020). Every weekday of 2018 counts as a session, so volatility and Sharpe are slightly overstated for every run alike.
* **Sale proceeds before December 2020:** the engine assumes the whole sale could be used the same day (observed in October 2020 and applied earlier). The two-step switch does not rely on it.
* **No rejected orders** in either version. A few comparison runs (other lookbacks, and the reality checks) had a buy refused for cash right after a sale while only part of the sale's money was usable. The strategy retried the next day.

## How to verify

* **`reports/signals.csv`** has every daily candle from 1 Jan 2018:
  * both closes and both 200-day EMAs, and whether each close is above its EMA;
  * each ETF's 3- and 12-month return, worked out again from Historify's closes;
  * the quarterly check days and the ETF each lookback picked;
  * what each version held after each day's fills.
* **Trades:** `reports/trades.csv` (12-month) and `reports/trades_3m.csv` (3-month) list every trade.
* **Cross-check:** replaying the rules day by day on the recomputed returns and EMAs gives the same trades as the engine, with the same entry and exit days: 27 of 27 (12-month) and 34 of 34 (3-month) (`reports/trade_check.csv`).

## Next steps

1. **A longer history, rules unchanged.** Test the 3-month version with the EMA filter on data from 2010, once Historify has it. Note that this broker returned GOLDBEES only from 2015, so the extra years may need another source.
2. **A walk-forward on the lookback.** Choose the lookback (3, 6, 9, 12 months) on past data only, and see whether the choice holds up on the next stretch. That tests whether "3 months" is a finding or a lucky pick.
3. **Momentum as a tilt instead of a switch.** Keep the 50:50 mix and lean it towards the stronger ETF above its EMA, so one wrong call cannot move the whole account.

## Run

```bash
cd strategies/06_niftybees_goldbees_dual_momentum_d_long
python strategy.py
```

Needs openalgo 2.4.0 or later, the OpenAlgo server running, and daily candles in Historify for NIFTYBEES and GOLDBEES (NSE) and NIFTY (NSE_INDEX) from 22 Nov 2016 to 20 Nov 2026.

## Files

| File | What it is |
|---|---|
| `strategy.py` | The rules, the variants, the yardsticks, the checks and the report |
| `reports/strategy_report.html` | Plotly report: both comparison tables, account value, drawdown, each ETF's 12- and 3-month return with what the strategy held, each ETF with its 200-day EMA, rolling returns |
| `reports/tearsheet.html`, `reports/tearsheet_3m.html` | The engine's tearsheets for the two lookbacks |
| `reports/run_log.txt` | The printed report of the run |
| `reports/signals.csv`, `trades.csv`, `trades_3m.csv`, `open_positions.csv` | Signals and trades to check against a chart |
| `reports/compared.csv`, `rolling_returns.csv` | Every run compared, and the rolling return table |
| `reports/trade_check.csv`, `stray_opens.csv` | The cross-check and the stray-open fills |
| `reports/tables/` | Every table of the baseline run |
