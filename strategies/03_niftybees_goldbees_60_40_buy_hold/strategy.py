"""
Strategy 03: NIFTYBEES and GOLDBEES, 60:40, buy and hold

Idea      : Put 60 percent of the money in the NIFTY 50 (NIFTYBEES) and 40 percent in
            gold (GOLDBEES) on the first day, and hold both without ever trading again.
            Shares and gold often move differently, so the mix should fall less than
            shares alone.
Market    : NIFTYBEES and GOLDBEES, NSE cash market (ETFs), daily candles
Entry     : On the first day of the test, at its close, place two market buy orders for
            60 percent and 40 percent of 95 percent of the account (5 percent stays in cash,
            as in strategies 01 and 02), in whole units. They fill at the OPEN of the next
            day. Note: ETF opening prices can carry stray trades; NIFTYBEES opened at 193.40
            on 23 Nov 2021, between closes of 188.53 and 189.40, so its buy cost about
            2 percent more than at that day's close.
Exit      : None. Both holdings are kept to the end and valued at the last close.
Rebalance : None. The weights drift with the prices (the comparison runs show a yearly
            rebalance too).
Product   : CNC (delivery).
Capital   : Rs 10,00,000.
Costs     : The engine's delivery charges for shares (STT, exchange charges, SEBI fee,
            stamp duty, GST) and slippage. Note: the engine charges ETF units like ordinary
            shares, 0.1 percent STT on the buy; under the STT rules equity ETF units pay STT
            only when sold (0.001 percent) and gold ETFs pay none, so the charges here are
            overstated by about Rs 1,000. Selling at the end would add a little more.
Period    : 22 Nov 2021 to 20 Nov 2026 (5 years).
Data      : Historify on your OpenAlgo server (source="db"), daily candles.

Run       : python strategy.py   (from this folder; needs openalgo 2.3.0 or later, the
            OpenAlgo server running, and OPENALGO_API_KEY in the .env file of
            "backtesting examples")
Outputs   : printed report, and in reports/: tearsheet.html, holdings.csv, prices.csv,
            and every table of the run in reports/tables/
"""
import os
from pathlib import Path

import pandas as pd

import openalgo.backtest as bt
from openalgo import api

# Where things are
HERE = Path(__file__).resolve().parent
REPORTS = HERE / "reports"

# The test settings, shared by every run in this file
START = "2021-11-22"
END = "2026-11-20"
CAPITAL = 10_00_000  # Rs 10 lakh
ETFS = ("NIFTYBEES", "GOLDBEES")


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


class BuyAndHold6040(bt.Strategy):
    symbols, exchange, interval = ETFS, "NSE", "D"
    nifty_pct = 60              # percent of the account in NIFTYBEES; GOLDBEES gets the rest (40)
    rebalance_every = "never"   # "never", or "year" to go back to 60:40 at the start of every year
    cash_buffer = 5             # percent of the account kept in cash, so a higher open still fills

    # init runs before the first day: set up the yearly rebalance, if asked for.
    def init(self):
        if self.rebalance_every != "never":
            self.every(self.rebalance_every, self.rebalance_now)

    # on_bar runs at the close of every day. On the first day only, buy the mix.
    def on_bar(self, bars):
        if not self.state.get("invested"):
            self.state["invested"] = True
            self.rebalance_now()

    # Buy (or trim and top up) so that each ETF holds its share of the account.
    def rebalance_now(self):
        self.rebalance({"NIFTYBEES": self.nifty_pct, "GOLDBEES": 100 - self.nifty_pct},
                       cash_buffer=self.cash_buffer)


def historify_daily(symbol):
    """Daily candles of one ETF from Historify."""
    bars = client.history(symbol=symbol, exchange="NSE", interval="D",
                          start_date=START, end_date=END, source="db")
    if not hasattr(bars, "index"):
        raise SystemExit(f"Historify returned no daily candles for {symbol}: {bars}")
    return bars


def stats(result):
    """The figures that describe a buy-and-hold portfolio."""
    m = result.metrics
    return {
        "Start value (Rs)": m["start_equity"],
        "End value (Rs)": m["end_equity"],
        "Net profit (Rs)": m["net_profit"],
        "Total return": m["total_return"],
        "CAGR": m["cagr"],
        "Volatility (yearly)": m["volatility"],
        "Sharpe ratio": m["sharpe"],
        "Sortino ratio": m["sortino"],
        "Calmar ratio": m["calmar"],
        "Max drawdown": m["max_drawdown"],
        "Max drawdown (Rs)": m["max_drawdown_amount"],
        "Longest drawdown (days)": m["longest_drawdown_days"],
        "Best year": m["best_year"],
        "Worst year": m["worst_year"],
        "Best month": m["best_month"],
        "Worst month": m["worst_month"],
        "Best day": m["best_session"],
        "Worst day": m["worst_session"],
        "Days up": m["session_win_rate"],
        # total_costs counts closed trades only; a buy and hold closes none, so add up the fills.
        "Charges (Rs)": result.costs["charged"].sum(),
        "Slippage (Rs)": result.fills["slippage_rupees"].sum(),
    }


def day(timestamp):
    """A date for printing, or a note when there is none (a fall not yet recovered)."""
    return "not yet" if timestamp is None or pd.isna(timestamp) else str(pd.Timestamp(timestamp).date())


def fmt(name, value):
    if "(Rs)" in name:
        return f"{value:,.2f}"
    if "(days)" in name:
        return f"{value:,.0f}"
    if "ratio" in name:
        return f"{value:.2f}"
    return f"{value:.2%}"


if __name__ == "__main__":
    REPORTS.mkdir(exist_ok=True)
    # Every run reads Historify (source="db"): the same candles, the same settings.
    # Market orders fill at the next day's open (the engine's default).
    run = dict(start=START, end=END, capital=CAPITAL, source="db")

    # 1. The portfolio: 60:40 on day one, then hold
    result = bt.backtest(BuyAndHold6040, client, **run)
    print(result.summary())
    print("\n== NIFTYBEES 60 : GOLDBEES 40, bought once and held")
    for name, value in stats(result).items():
        print(f"  {name:<26}: {fmt(name, value)}")
    m = result.metrics
    print(f"  Worst fall: from the high of {day(m['max_drawdown_peak'])} to the low of "
          f"{day(m['max_drawdown_trough'])}; back above that high: {day(m['max_drawdown_recovery'])}")
    below_peak = m["end_equity"] / result.equity["equity_rupees"].max() - 1
    print(f"  On {END} the portfolio is {below_peak:.2%} below its highest value")

    # 2. What was bought and what it is worth now
    fills = result.fills.set_index("symbol")
    held = result.final_positions.set_index("symbol")
    holdings = pd.DataFrame({
        "units": held["quantity_units"],
        "buy_price": fills["price_rupees"],
        "cost": held["quantity_units"] * fills["price_rupees"],
        "last_close": held["mark_rupees"],
        "value_now": held["value_rupees"],
        "profit": held["unrealized_rupees"],
    })
    holdings["weight_at_start"] = holdings["cost"] / holdings["cost"].sum()
    holdings["weight_now"] = holdings["value_now"] / holdings["value_now"].sum()
    holdings["return"] = holdings["value_now"] / holdings["cost"] - 1
    print("\n== Holdings")
    print(holdings.to_string(formatters={
        "units": "{:,.0f}".format, "buy_price": "{:,.2f}".format, "cost": "{:,.2f}".format,
        "last_close": "{:,.2f}".format, "value_now": "{:,.2f}".format, "profit": "{:,.2f}".format,
        "weight_at_start": "{:.1%}".format, "weight_now": "{:.1%}".format, "return": "{:.2%}".format,
    }))
    cash = m["end_equity"] - holdings["value_now"].sum()
    print(f"  Cash left over (not invested): Rs {cash:,.2f}")

    # 3. The same money in other ways, for comparison
    others = {
        "60:40, rebalanced every year": bt.backtest(BuyAndHold6040, client, **run,
                                                    params={"rebalance_every": "year"}),
        "NIFTYBEES only (100%)": bt.backtest(BuyAndHold6040, client, **run, params={"nifty_pct": 100}),
        "GOLDBEES only (100%)": bt.backtest(BuyAndHold6040, client, **run, params={"nifty_pct": 0}),
    }
    rows = {"60:40, bought once (this strategy)": result, **others}
    table = pd.DataFrame({
        label: {
            "Net profit (Rs)": r.metrics["net_profit"],
            "CAGR": r.metrics["cagr"],
            "Volatility": r.metrics["volatility"],
            "Max drawdown": r.metrics["max_drawdown"],
            "Sharpe": r.metrics["sharpe"],
        }
        for label, r in rows.items()
    }).T
    print("\n== Compared with other ways of holding the same Rs 10 lakh")
    print(table.to_string(formatters={
        "Net profit (Rs)": "{:,.2f}".format, "CAGR": "{:.2%}".format, "Volatility": "{:.2%}".format,
        "Max drawdown": "{:.2%}".format, "Sharpe": "{:.2f}".format,
    }))

    # 4. Year by year: the portfolio and each ETF on its own
    yearly = pd.DataFrame({
        "60:40": result.performance.yearly_returns,
        "NIFTYBEES": others["NIFTYBEES only (100%)"].performance.yearly_returns,
        "GOLDBEES": others["GOLDBEES only (100%)"].performance.yearly_returns,
    })
    print("\n== Year by year (2021 is 23 Nov to 31 Dec; 2026 is to 20 Nov)")
    print(yearly.to_string(float_format="{:.2%}".format))

    # 5. Why the mix helps: how closely the two ETFs move together
    prices = pd.DataFrame({s: historify_daily(s)["close"] for s in ETFS})
    correlation = prices.pct_change().corr().loc["NIFTYBEES", "GOLDBEES"]
    print(f"\n  Correlation of daily returns, NIFTYBEES and GOLDBEES: {correlation:.2f}"
          "  (1 = move together, 0 = unrelated, -1 = opposite)")

    # 6. Warnings
    print("\n== Warnings")
    for line in result.warnings:
        print("  -", line)

    # 7. Files to verify and share
    holdings.to_csv(REPORTS / "holdings.csv")
    prices.to_csv(REPORTS / "prices.csv")
    result.to_csv(str(REPORTS / "tables"))
    result.tearsheet(str(REPORTS / "tearsheet.html"))
    print(f"\nSaved: {REPORTS / 'tearsheet.html'}")
    print(f"       {REPORTS / 'holdings.csv'}")
    print(f"       {REPORTS / 'prices.csv'}")
    print(f"       {REPORTS / 'tables'}")
