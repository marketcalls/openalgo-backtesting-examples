"""
Strategy 01: SBIN Supertrend (10, 3) on hourly candles, long only

Idea      : Ride SBIN's up-moves on the hourly chart. Hold while the Supertrend is
            green (price above the line), stay out while it is red.
Market    : SBIN, NSE cash market, 1-hour candles (09:15, 10:15, ... the last candle of the day)
Indicator : Supertrend, ATR period 10, multiplier 3.0 (the line sits 3 ATRs from the price)
Entry     : When the Supertrend turns green (flips from red to green) at the close of a
            candle and no shares are held, BUY at MARKET. The order fills at the OPEN of
            the next candle.
Exit      : When the Supertrend is red at the close of a candle while shares are held,
            SELL ALL at MARKET at the OPEN of the next candle. There is no separate
            stop-loss or target: the red flip is the exit.
Last candle of the day: a signal at the close of the day's last candle has no candle left
            that day, so its order is placed at 09:15 the next trading day and fills at
            that day's open.
Direction : Long only. The strategy never sells short.
Product   : CNC (delivery). Shares are held overnight for as long as the trend lasts.
Capital   : Rs 10,00,000 at the start.
Size      : 95 percent of the account value on each buy, in whole shares (5 percent is kept
            back so a gap up at the next open does not leave the order short of money).
Costs     : Indian delivery charges at each trade date's rates (STT, exchange charges, SEBI
            fee, stamp duty, GST, DP charge; zero delivery brokerage) and slippage of
            2 basis points on every fill.
Period    : 22 Nov 2021 to 20 Nov 2026 (5 years). Candles before the start warm up the indicator.
Data      : Historify on your OpenAlgo server (source="db"). Historify stores 1-minute
            candles; the engine builds the hourly candles from them and fills each order
            at the open of the first minute of the next hourly candle.

Run       : python strategy.py   (from this folder; needs openalgo 2.3.0 or later, the
            OpenAlgo server running, and OPENALGO_API_KEY in the .env file of
            "backtesting examples")
Outputs   : printed report, and in reports/: tearsheet.html, trades.csv, signals.csv,
            and every table of the run in reports/tables/
"""
import os
from datetime import time
from pathlib import Path

import openalgo.backtest as bt
from openalgo import api, ta

# Where things are
HERE = Path(__file__).resolve().parent
REPORTS = HERE / "reports"

# The test settings, shared by every run in this file
START = "2021-11-22"
END = "2026-11-20"
CAPITAL = 10_00_000          # Rs 10 lakh
MARKET_CLOSE = time(15, 30)  # NSE cash session close
SIGNALS_FROM = "2020-01-01"  # hourly candles read for signals.csv, so the indicator is warmed up


def load_env():
    """Read KEY=VALUE lines from the nearest .env file above this script into the environment."""
    for folder in HERE.parents:
        env_file = folder / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                name, sep, value = line.partition("=")
                if sep and name.strip() and not name.strip().startswith("#"):
                    os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))
            return


# Connect to the OpenAlgo server. The key comes from the .env file, never from this script.
load_env()
client = api(api_key=os.environ["OPENALGO_API_KEY"],
             host=os.environ.get("OPENALGO_HOST", "http://127.0.0.1:5000"))


class SupertrendLongOnly(bt.Strategy):
    symbol, exchange, interval = "SBIN", "NSE", "1h"
    product = "CNC"   # delivery: hold overnight (hourly candles would otherwise trade MIS, closed every day)
    period = 10       # ATR period of the Supertrend
    multiplier = 3.0  # distance of the line from the price, in ATRs
    size = 95         # percent of the account value put into each buy

    # init runs before the first candle: set up the indicator and the 09:15 timer.
    def init(self):
        # ta.supertrend returns the line and its direction: -1 = green (uptrend), 1 = red (downtrend).
        self.st_line, self.st_direction = self.I(
            ta.supertrend, self.high, self.low, self.close, self.period, self.multiplier
        )
        # Every trading day at 09:15: place an order that yesterday's last candle could not.
        self.at("09:15", self.at_open)

    # on_bar runs at the close of every hourly candle.
    def on_bar(self, bar):
        turned_green = self.st_direction.crossed_below(0)  # direction moved from 1 (red) to -1 (green) on this candle
        is_red = self.st_direction[-1] > 0                 # this candle closed in a downtrend

        # What the strategy wants to hold: shares after a green flip, nothing while red.
        if turned_green:
            self.state["want"] = "long"
        elif is_red:
            self.state["want"] = "flat"

        # The day's last candle: the market has closed, so the 09:15 timer places the order tomorrow.
        if bar.close_time.time() >= MARKET_CLOSE:
            return
        self.trade_to_want()

    # Called by the timer at 09:15 every trading day; its order fills at the 09:15 open.
    def at_open(self):
        self.trade_to_want()

    # Buy or sell so that the position matches what the strategy wants.
    def trade_to_want(self):
        if self.orders:  # an order is already waiting to fill
            return
        want = self.state.get("want")
        if want == "long" and self.position.is_flat:
            self.buy(size=bt.size.percent(self.size))  # market order
        elif want == "flat" and self.position.is_long:
            self.exit()                                # sell all shares, market order


class BuyAndHold(bt.Strategy):
    """The yardstick: buy SBIN on the first candle with the same money and simply hold it."""
    symbol, exchange, interval = "SBIN", "NSE", "1h"
    product = "CNC"

    def on_bar(self, bar):
        if self.position.is_flat:
            self.buy(size=bt.size.percent(95))


def historify_hourly(start, end):
    """SBIN's hourly candles from Historify (built from its 1-minute candles), for signals.csv."""
    bars = client.history(symbol="SBIN", exchange="NSE", interval="1h",
                          start_date=start, end_date=end, source="db")
    if not hasattr(bars, "index"):
        raise SystemExit(f"Historify returned no hourly candles: {bars}")
    return bars


def headline(result):
    """The figures a trader reads first, worked out from the run."""
    m = result.metrics
    trades = result.trade_list()
    wins = trades[trades["net_pnl"] > 0]
    losses = trades[trades["net_pnl"] <= 0]
    return {
        "Net profit (Rs)": m["net_profit"],
        "Return": m["total_return"],
        "CAGR": m["cagr"],
        "Max drawdown": m["max_drawdown"],
        "Sharpe ratio": m["sharpe"],
        "Closed trades": len(trades),
        "Win rate": len(wins) / len(trades) if len(trades) else float("nan"),
        "Average win (Rs)": wins["net_pnl"].mean() if len(wins) else 0.0,
        "Average loss (Rs)": losses["net_pnl"].mean() if len(losses) else 0.0,
        "Profit factor": m["profit_factor"],
        "Time in market": m["exposure"],
        "Charges (Rs)": m["total_costs"],
        "Slippage (Rs)": m["total_slippage"],
    }


def show(title, figures):
    print(f"\n== {title}")
    for name, value in figures.items():
        if "(Rs)" in name:
            print(f"  {name:<20}: {value:,.2f}")
        elif name in ("Closed trades",):
            print(f"  {name:<20}: {value}")
        elif name in ("Sharpe ratio", "Profit factor"):
            print(f"  {name:<20}: {value:.2f}")
        else:
            print(f"  {name:<20}: {value:.2%}")


def save_signals(bars, path):
    """Every hourly candle with the Supertrend line and colour, to check the trades on a chart."""
    line, direction = ta.supertrend(bars["high"], bars["low"], bars["close"],
                                    SupertrendLongOnly.period, SupertrendLongOnly.multiplier)
    signals = bars[["open", "high", "low", "close"]].copy()
    signals["supertrend"] = line.round(2)
    signals["colour"] = direction.map({-1: "green", 1: "red"})
    signals["flip"] = ""
    previous = direction.shift(1)
    signals.loc[(previous == 1) & (direction == -1), "flip"] = "turned green: BUY at next open"
    signals.loc[(previous == -1) & (direction == 1), "flip"] = "turned red: SELL at next open"
    signals.loc[START:END].to_csv(path)


if __name__ == "__main__":
    REPORTS.mkdir(exist_ok=True)
    # Every run reads Historify (source="db"): the same candles, the same settings.
    run = dict(start=START, end=END, capital=CAPITAL, source="db")

    # 1. The backtest
    result = bt.backtest(SupertrendLongOnly, client, **run)
    print(result.summary())
    show("Strategy: Supertrend (10, 3), hourly, long only", headline(result))

    trades = result.trade_list()
    print("\n  How the trades ended:", trades["exit_reason"].value_counts().to_dict())
    print(f"  Average holding: {trades['bars_held'].mean():.1f} hourly candles, {trades['days_held'].mean():.1f} calendar days")

    print("\n== Year by year")
    for year, value in result.performance.yearly_returns.items():
        print(f"  {year}: {value:7.2%}")

    # 2. The yardstick: did the strategy beat simply holding SBIN?
    hold = bt.backtest(BuyAndHold, client, **run)
    hm = hold.metrics
    print("\n== Buy and hold SBIN with the same Rs 10 lakh")
    print(f"  Net profit (Rs)     : {hm['net_profit']:,.2f}")
    print(f"  Return              : {hm['total_return']:.2%}")
    print(f"  CAGR                : {hm['cagr']:.2%}")
    print(f"  Max drawdown        : {hm['max_drawdown']:.2%}")

    # 3. Reality checks: worse fills and late orders
    print("\n== Reality checks (profit kept versus the backtest)")
    base_profit = result.metrics["net_profit"]
    checks = {
        "Filled at the next candle's close": bt.backtest(SupertrendLongOnly, client, **run, fill="next_close"),
        "Every order one candle late": bt.backtest(SupertrendLongOnly, client, **run, delay_entries=1, delay_exits=1),
    }
    for label, check in checks.items():
        profit = check.metrics["net_profit"]
        kept = profit / base_profit if base_profit > 0 else float("nan")
        print(f"  {label:<34}: Rs {profit:,.2f} ({kept:.0%} kept)")

    # 4. Warnings: what the engine assumed or refused
    print("\n== Warnings")
    for line in result.warnings:
        print("  -", line)

    # 5. Files to verify and share
    columns = ["entry_time", "exit_time", "quantity", "entry_price", "exit_price",
               "net_pnl", "return_pct", "bars_held", "days_held", "charges", "exit_reason"]
    trades[columns].to_csv(REPORTS / "trades.csv")
    save_signals(historify_hourly(SIGNALS_FROM, END), REPORTS / "signals.csv")
    result.to_csv(str(REPORTS / "tables"))
    result.tearsheet(str(REPORTS / "tearsheet.html"))
    print(f"\nSaved: {REPORTS / 'tearsheet.html'}")
    print(f"       {REPORTS / 'trades.csv'}")
    print(f"       {REPORTS / 'signals.csv'}")
    print(f"       {REPORTS / 'tables'}")
