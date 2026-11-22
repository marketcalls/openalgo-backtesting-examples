# Research 01: the least correlated NIFTY 50 stocks

**Question:** which NIFTY 50 stocks move least alike, so that a basket of them is as diversified as a NIFTY 50 basket can be?

**Answer (22 Nov 2021 to 20 Nov 2026):** MAXHEALTH, ONGC, HINDUNILVR, ETERNAL, CIPLA, INFY, POWERGRID, BAJAJ-AUTO, KOTAKBANK and ADANIENT, one from each of ten sectors. Their average pair correlation is 0.155, against 0.271 for all NIFTY 50 pairs.

Shareable page with the method, the reasoning and every chart: https://claude.ai/artifact/Jfu3Lds4zG2viY33pfA2nm (private until you share it from its Share menu).

## How it was done

1. **Clean daily closes** from Historify for 49 NIFTY 50 stocks (the 50th constituent was not found in Historify), 1,241 trading days. One corporate-action day left out: TMPV on 14 Oct 2025 (Tata Motors demerger). Real crashes stay in.
2. **Daily returns, not prices**, so two stocks that both rose over five years do not look alike for that reason alone.
3. **Correlation of every pair** (1,176 pairs). The average pair is 0.271.
4. **Each stock's average correlation** with the other 48. Lowest: MAXHEALTH 0.15, CIPLA 0.15, DRREDDY 0.18, ONGC 0.19, HINDUNILVR 0.20.
5. **Greedy basket, one stock per sector:** start with the lowest average, then keep adding the stock least correlated with those already chosen. Taking the ten lowest averages would fail: INFY and TCS are both among them but move together at 0.74.
6. **Ten stocks:** the basket's average pair correlation rises from 0.04 (2 stocks) to 0.155 (10) and 0.21 (16, one per sector).
7. **Against chance:** none of 2,000 random 10-stock baskets was less correlated. Volatility fell less: an equal-weight basket swung 14.91 percent a year against 15.62 percent for the median random basket, because these stocks swing more on their own.
8. **Out of sample:** picked on 2021 to 2024 only, the basket (7 of the same 10 stocks) had 0.141 correlation then and 0.226 on 2024 to 2026, against 0.265 and 0.280 for all pairs. The advantage shrank but held.

## Limits

* All 49 are Indian large-cap equities: in a market-wide fall they drop together (4 Jun 2024: ONGC -16.8%, POWERGRID -12.4%, ADANIENT -19.3%). GOLDBEES had an average correlation of 0.045 with these stocks, lower than any stock basket.
* Correlation says nothing about returns. Next step: backtest the basket (equal weight, rebalanced yearly) against NIFTYBEES and strategy 03's 60:40 mix.
* Sectors are broad groups set by hand in `select_basket.py`.

## Run it

From this folder, with the OpenAlgo server running (needs pandas, numpy and plotly; no backtesting engine):

```bash
python select_basket.py
```

To add the 50th NIFTY 50 stock, add it with a sector to `SECTORS` at the top of the script.

## Files

| File | What it is |
|---|---|
| `select_basket.py` | Fetches the data, does every step, writes everything below |
| `page_template.html` | The shareable page; the script fills in the numbers |
| `reports/correlation_page.html` | The shareable page (published as the artifact above) |
| `reports/correlation_report.html` | The same Plotly charts as one offline page |
| `reports/correlation_matrix.csv` | Correlation of every pair |
| `reports/average_correlation.csv` | Each stock's average correlation with the rest, with its sector |
| `reports/basket.csv` | The basket, in the order chosen |
| `reports/out_of_sample.csv` | The out-of-sample check |
| `reports/random_baskets.csv` | The 2,000 random baskets' correlation and volatility |
