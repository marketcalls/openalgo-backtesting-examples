# OpenAlgo Backtesting Examples

Backtests of trading ideas for Indian markets, built with the OpenAlgo backtesting engine (`openalgo.backtest`) on price data from Historify, the candle database of an OpenAlgo server. Each strategy has its own folder with the rules in code, a README that explains the rules in plain words, how to verify every trade, the results and a verdict, and the reports the run produced.

The results include the strategies that did not work. A backtest that shows an idea is not worth trading is a useful result.

## What is here

| Folder | What it is |
|---|---|
| [`strategies/`](strategies/README.md) | One folder per strategy, numbered in the order tested, with a log comparing them all |
| [`research/`](research/01_nifty50_low_correlation/README.md) | Studies that feed the strategies, such as picking the least correlated NIFTY 50 stocks |
| [`quant_persona.md`](quant_persona.md) | The working rules every strategy follows: data, fills, costs, checks, verdicts, charts and folder layout |
| `data/` | An earlier broker-API downloader and the hourly SBIN candles it saved (the strategies now read Historify instead) |

## Strategies so far

| No. | Strategy | Verdict |
|---|---|---|
| 01 | Supertrend (10, 3), hourly, long only, SBIN | Reject (to be rerun on Historify data) |
| 02 | Supertrend (10, 3) with an EMA 200 filter, hourly, long only, SBIN | Pending a rerun on Historify data |
| 03 | NIFTYBEES 60 : GOLDBEES 40, buy and hold | Reference portfolio: 13.03% a year, worst fall 18.88% |
| 04 | Supertrend (10, 3), hourly, long only, on the 10 least correlated NIFTY 50 stocks | Reject: 5.80% a year against 12.63% for holding the same stocks |
| 05 | Two strategies on one Rs 10 lakh account, hourly, long only: UT Bot 60% (SBIN, RELIANCE, MAXHEALTH, CIPLA) and Supertrend (10, 3) 40% (SUNPHARMA, ICICIBANK, TATASTEEL, MARUTI) | Reject: -4.34% a year against 14.59% for holding the same 8 stocks |
| 06 | Momentum switch between NIFTYBEES and GOLDBEES (Antonacci's dual momentum, crash filter removed) with a 200-day EMA entry and exit filter, daily candles, checked every quarter, 12- and 3-month lookbacks | Not enough evidence: 3-month version 15.79% a year (worst fall 24.02%) against 14.40% (worst fall 19.53%) for a 50:50 mix of the same ETFs; the 12-month version made 10.33% |

Details, figures and reasons are in [`strategies/README.md`](strategies/README.md) and each strategy's own README.

## How to run

1. **An OpenAlgo server**, running and logged in to your broker, with the symbols' candles downloaded in Historify (1-minute candles for intraday strategies, daily candles for daily ones). See the [OpenAlgo documentation](https://docs.openalgo.in).
2. **Python 3.12 or newer**, and the packages:

   ```bash
   pip install -U openalgo plotly pandas numpy
   ```

   The backtesting engine needs openalgo 2.3.0 or later.
3. **Your API key**: copy `.env.example` to `.env` in this folder and put your key in it. `.env` is ignored by git; never commit it.
4. **Run a strategy** from its folder:

   ```bash
   cd strategies/04_nifty50_basket_supertrend_1h_long
   python strategy.py
   python tearsheet.py
   ```

Every script prints its report and writes its files to `reports/` in its own folder.

## How the backtests work

* Data comes from Historify (`source="db"`). Intraday strategies use 1-minute candles, from which the engine builds the hourly ones.
* Market orders fill at the open of the next candle, with slippage.
* Indian charges are applied at each trade date's rates (STT, exchange charges, SEBI fee, stamp duty, GST, DP charge).
* Every strategy is compared with simply holding, tested with worse fills and late orders, and checked for overfitting.
* Charts are drawn with Plotly.

## Disclaimer

For education and research only. Nothing here is investment advice or a recommendation to buy or sell any security. Backtests describe the past under stated assumptions, and real trading can differ. Test any strategy in OpenAlgo's sandbox mode (analyzer mode) before risking money.

## License

[MIT](LICENSE)
