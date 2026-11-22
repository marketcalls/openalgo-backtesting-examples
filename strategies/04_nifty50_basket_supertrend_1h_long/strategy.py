"""
Strategy 04: Supertrend (10, 3) on hourly candles, long only, on the 10 least correlated
NIFTY 50 stocks, with an equal share of the money for each stock

Idea      : Strategy 01's Supertrend rules, spread over the 10-stock basket from
            research/01_nifty50_low_correlation. Each stock is traded on its own signal;
            because the stocks move least alike, their trades should not all win or lose
            together.
Stocks    : MAXHEALTH, ONGC, HINDUNILVR, ETERNAL, CIPLA, INFY, POWERGRID, BAJAJ-AUTO,
            KOTAKBANK, ADANIENT (NSE cash market), 1-hour candles
Indicator : Supertrend, ATR period 10, multiplier 3.0, on each stock's own candles
Entry     : When a stock's Supertrend turns green (red to green) at the close of a candle
            and that stock is not held, BUY it at MARKET; the order fills at the OPEN of
            the next candle.
Exit      : When a stock's Supertrend is red at the close of a candle while it is held,
            SELL ALL of it at MARKET at the OPEN of the next candle. No stop-loss or target.
Last candle of the day: a signal at the close of the day's last candle is placed at 09:15
            the next trading day and fills at that day's open.
Direction : Long only.
Product   : CNC (delivery), held overnight.
Capital   : Rs 10,00,000.
Equal allocation: each buy is 9.5 percent of the account value at that moment, in whole
            shares, so 10 stocks held at once fill 95 percent and 5 percent stays in cash
            (as in strategies 01 to 03). A stock not held keeps its share in cash.
Costs     : Indian delivery charges at each trade date's rates, slippage 2 basis points.
Period    : 22 Nov 2021 to 20 Nov 2026. Historify's candles start on 22 Nov 2021, so each
            stock waits about 3.5 months inside the run for its Supertrend to warm up
            (512 hourly candles) and the first trade comes in March 2022.
Data      : Historify (source="db"): 1-minute candles, from which the engine builds the
            hourly ones; daily candles for the buy-and-hold yardsticks.

Run       : python strategy.py   (from this folder; needs openalgo 2.3.0 or later, plotly,
            the OpenAlgo server running, and OPENALGO_API_KEY in the .env file of
            "backtesting examples")
Outputs   : printed report, and in reports/: strategy_report.html (Plotly charts),
            tearsheet.html, trades.csv, by_stock.csv, signals.csv, tables/
"""
import os
from datetime import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

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
BASKET = ("MAXHEALTH", "ONGC", "HINDUNILVR", "ETERNAL", "CIPLA",
          "INFY", "POWERGRID", "BAJAJ-AUTO", "KOTAKBANK", "ADANIENT")
DONE = {"Filled", "Rejected", "Cancelled", "Expired"}  # order states that are no longer waiting


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


class SupertrendBasket(bt.Strategy):
    symbols, exchange, interval = BASKET, "NSE", "1h"
    product = "CNC"    # delivery: hold overnight (hourly candles would otherwise trade MIS)
    period = 10        # ATR period of the Supertrend
    multiplier = 3.0   # distance of the line from the price, in ATRs
    alloc_pct = 9.5    # percent of the account put into each buy (10 stocks x 9.5 = 95)

    # init runs before the first candle: one Supertrend per stock, and the 09:15 timer.
    def init(self):
        self.direction = {}  # per stock: -1 = green (uptrend), 1 = red (downtrend)
        for s in self.symbols:
            d = self.data[s]
            _line, self.direction[s] = self.I(ta.supertrend, d.high, d.low, d.close,
                                              self.period, self.multiplier)
        self.last_order = {}  # per stock: the last order sent, to avoid sending a second while it waits
        self.at("09:15", self.at_open)

    # on_bar runs at the close of every hourly candle; `bars` holds the stocks that are ready.
    def on_bar(self, bars):
        want = self.state.setdefault("want", {})
        for s in bars:
            if self.direction[s].crossed_below(0):   # turned green on this candle
                want[s] = "long"
            elif self.direction[s][-1] > 0:          # red on this candle
                want[s] = "flat"
        # The day's last candle: the market has closed, so the 09:15 timer acts tomorrow.
        if any(bar.close_time.time() >= MARKET_CLOSE for bar in bars.values()):
            return
        for s in bars:
            self.trade_to_want(s)

    # Called by the timer at 09:15 every trading day; its orders fill at the 09:15 open.
    def at_open(self):
        for s in self.symbols:
            self.trade_to_want(s)

    # Buy or sell one stock so that its position matches what the strategy wants.
    def trade_to_want(self, s):
        order = self.last_order.get(s)
        if order is not None and order.status not in DONE:  # its last order is still waiting
            return
        want = self.state.get("want", {}).get(s)
        if want == "long" and self.positions[s].is_flat:
            self.last_order[s] = self.buy(symbol=s, size=bt.size.percent(self.alloc_pct))
        elif want == "flat" and self.positions[s].is_long:
            self.last_order[s] = self.exit(symbol=s)


class EqualWeightHold(bt.Strategy):
    """Yardstick 1: the same 10 stocks, 9.5 percent each, bought on day one and held."""
    symbols, exchange, interval = BASKET, "NSE", "D"

    def on_bar(self, bars):
        if not self.state.get("invested"):
            self.state["invested"] = True
            self.rebalance({s: 10 for s in self.symbols}, cash_buffer=5)


class NiftyBeesHold(bt.Strategy):
    """Yardstick 2: the NIFTY 50 itself (NIFTYBEES), 95 percent bought on day one and held."""
    symbol, exchange, interval = "NIFTYBEES", "NSE", "D"

    def on_bar(self, bar):
        if self.position.is_flat:
            self.buy(size=bt.size.percent(95))


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
        "Volatility (yearly)": m["volatility"],
        "Sharpe ratio": m["sharpe"],
        "Closed trades": len(trades),
        "Win rate": len(wins) / len(trades) if len(trades) else float("nan"),
        "Average win (Rs)": wins["net_pnl"].mean() if len(wins) else 0.0,
        "Average loss (Rs)": losses["net_pnl"].mean() if len(losses) else 0.0,
        "Profit factor": m["profit_factor"],
        "Time in market": m["exposure"],
        "Charges (Rs)": result.costs["charged"].sum(),
        "Slippage (Rs)": result.fills["slippage_rupees"].sum(),
    }


def show(title, figures):
    print(f"\n== {title}")
    for name, value in figures.items():
        if "(Rs)" in name:
            print(f"  {name:<20}: {value:,.2f}")
        elif name == "Closed trades":
            print(f"  {name:<20}: {value}")
        elif name in ("Sharpe ratio", "Profit factor"):
            print(f"  {name:<20}: {value:.2f}")
        else:
            print(f"  {name:<20}: {value:.2%}")


def first_decision(result):
    """The day the strategy could first act (the end of the indicators' warm-up)."""
    orders = result.orders
    return pd.Timestamp(orders["decided_at"].min()) if len(orders) else None


def by_stock(result, daily_closes):
    """Each stock's trades and profit in the strategy, beside its own buy-and-hold return."""
    trades = result.trade_list()
    held = result.final_positions.set_index("symbol") if len(result.final_positions) else pd.DataFrame()
    rows = []
    for s in BASKET:
        t = trades[trades["symbol"] == s]
        open_pnl = float(held.loc[s, "unrealized_rupees"]) if s in held.index else 0.0
        closes = daily_closes[s].dropna()
        rows.append({
            "symbol": s,
            "closed_trades": len(t),
            "win_rate": (t["net_pnl"] > 0).mean() if len(t) else float("nan"),
            "closed_pnl": t["net_pnl"].sum(),
            "open_pnl": open_pnl,
            "total_pnl": t["net_pnl"].sum() + open_pnl,
            "charges": t["charges"].sum(),
            "stock_return_buy_hold": closes.iloc[-1] / closes.iloc[0] - 1,
        })
    return pd.DataFrame(rows).set_index("symbol")


def historify(symbol, interval, start=START):
    bars = client.history(symbol=symbol, exchange="NSE", interval=interval,
                          start_date=start, end_date=END, source="db")
    if not hasattr(bars, "index"):
        raise SystemExit(f"Historify returned no {interval} candles for {symbol}: {bars}")
    return bars


def save_signals(path):
    """Every hourly candle of every stock with its Supertrend and colour, to check trades on a chart."""
    frames = []
    for s in BASKET:
        bars = historify(s, "1h", start="2021-01-01")
        line, direction = ta.supertrend(bars["high"], bars["low"], bars["close"],
                                        SupertrendBasket.period, SupertrendBasket.multiplier)
        f = bars[["open", "high", "low", "close"]].copy()
        f.insert(0, "symbol", s)
        f["supertrend"] = line.round(2)
        f["colour"] = direction.map({-1: "green", 1: "red"})
        prev = direction.shift(1)
        f["flip"] = ""
        f.loc[(prev == 1) & (direction == -1), "flip"] = "turned green: BUY at next open"
        f.loc[(prev == -1) & (direction == 1), "flip"] = "turned red: SELL at next open (if held)"
        frames.append(f.loc[START:END])
    pd.concat(frames).to_csv(path)


# ---------------------------------------------------------------- Plotly report
SURFACE, INK, INK_2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA, RED = "#2a78d6", "#eb6834", "#1baf7a", "#e34948"
FONT = "system-ui, -apple-system, Segoe UI, sans-serif"


def layout(fig, title, subtitle, height, left=80):
    fig.update_layout(
        title=dict(text=f"{title}<br><span style='font-size:13px;color:{INK_2}'>{subtitle}</span>",
                   x=0, xanchor="left", font=dict(size=18, color=INK)),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, height=height,
        font=dict(family=FONT, size=12, color=INK_2), margin=dict(l=left, r=150, t=100, b=50),
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=AXIS, font=dict(family=FONT, color=INK)),
        legend=dict(orientation="h", x=0, y=1.02, yanchor="bottom", font=dict(color=INK_2)),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont=dict(color=MUTED))
    return fig


def equity_chart(curves):
    """Account value of each way of investing the same Rs 10 lakh, on one rupee axis."""
    fig = go.Figure()
    for name, (series, colour) in curves.items():
        fig.add_trace(go.Scatter(x=series.index, y=series.values, name=name, mode="lines",
                                 line=dict(color=colour, width=2),
                                 hovertemplate=name + "<br>%{x|%d %b %Y}: Rs %{y:,.0f}<extra></extra>"))
        fig.add_annotation(x=series.index[-1], y=series.values[-1], xanchor="left", xshift=6, showarrow=False,
                           text=f"{name.split(' (')[0]}<br>Rs {series.values[-1] / 1e5:,.2f} lakh",
                           font=dict(color=INK_2, size=11), align="left")
    fig.add_hline(y=CAPITAL, line=dict(color=AXIS, width=1))
    layout(fig, "Account value, Rs 10 lakh invested three ways",
           f"{START} to {END}. The grey line is the starting Rs 10 lakh.", 480)
    fig.update_yaxes(title=dict(text="account value (Rs)", font=dict(color=MUTED)), tickformat=",.0f")
    fig.update_layout(hovermode="x unified")
    return fig


def drawdown_chart(curves):
    """How far each account was below its own highest value, day by day."""
    fig = go.Figure()
    for name, (series, colour) in curves.items():
        dd = series / series.cummax() - 1
        fig.add_trace(go.Scatter(x=dd.index, y=dd.values, name=name, mode="lines", line=dict(color=colour, width=2),
                                 hovertemplate=name + "<br>%{x|%d %b %Y}: %{y:.1%}<extra></extra>"))
        fig.add_annotation(x=dd.idxmin(), y=dd.min(), text=f"{dd.min():.1%}", showarrow=True, ax=0, ay=24,
                           arrowcolor=MUTED, font=dict(color=INK_2, size=11))
    layout(fig, "Drawdown: the fall from each account's highest value",
           "The lowest point of each line is its worst fall (max drawdown).", 420)
    fig.update_yaxes(title=dict(text="below the peak", font=dict(color=MUTED)), tickformat=".0%")
    fig.update_layout(hovermode="x unified")
    return fig


def stock_chart(table):
    """Each stock's profit in the strategy, ranked; blue made money, red lost."""
    t = table.sort_values("total_pnl")
    colours = [BLUE if v >= 0 else RED for v in t["total_pnl"]]
    fig = go.Figure(go.Bar(
        x=t["total_pnl"], y=t.index, orientation="h", marker=dict(color=colours),
        text=[f"Rs {v:,.0f}" for v in t["total_pnl"]], textposition="outside", cliponaxis=False,
        textfont=dict(color=INK_2),
        customdata=t[["closed_trades", "closed_pnl", "open_pnl", "stock_return_buy_hold"]].values,
        hovertemplate=("%{y}<br>profit Rs %{x:,.0f}<br>%{customdata[0]} closed trades, Rs %{customdata[1]:,.0f}"
                       "<br>still held: Rs %{customdata[2]:,.0f}<br>the stock itself: %{customdata[3]:.1%}<extra></extra>"),
    ))
    layout(fig, "Profit by stock in the strategy",
           "Closed trades plus any position still held on the last day, after charges.", 460, left=110)
    fig.update_layout(barcornerradius=4, bargap=0.35, showlegend=False)
    fig.update_xaxes(title=dict(text="profit (Rs)", font=dict(color=MUTED)), tickformat=",.0f")
    fig.update_yaxes(showgrid=False, tickfont=dict(color=INK_2))
    return fig


def write_report(figures, path):
    parts = [f"<html><head><meta charset='utf-8'><title>Strategy 04 report</title><style>body{{background:{SURFACE};"
             f"color:{INK};font-family:{FONT};max-width:1100px;margin:24px auto;padding:0 16px}}"
             f".chart{{margin:24px 0 40px}}</style></head><body><h1 style='font-size:24px'>Strategy 04: "
             f"Supertrend on the 10 least correlated NIFTY 50 stocks</h1>"]
    for i, fig in enumerate(figures):
        parts.append("<div class='chart'>" + fig.to_html(full_html=False, include_plotlyjs=(i == 0),
                                                       config={"displaylogo": False}) + "</div>")
    parts.append("</body></html>")
    path.write_text("".join(parts), encoding="utf-8")


if __name__ == "__main__":
    REPORTS.mkdir(exist_ok=True)
    # Every run reads Historify (source="db"); market orders fill at the next candle's open.
    run = dict(start=START, end=END, capital=CAPITAL, source="db")

    # 1. The strategy
    result = bt.backtest(SupertrendBasket, client, **run)
    print(result.summary())
    show("Strategy 04: Supertrend (10, 3), hourly, long only, 10 stocks at 9.5% each", headline(result))
    began = first_decision(result)
    print(f"  First order (after the Supertrend warm-up): {began}")
    trades = result.trade_list()
    print("  How the trades ended:", trades["exit_reason"].value_counts().to_dict())
    print(f"  Average holding: {trades['bars_held'].mean():.1f} hourly candles, {trades['days_held'].mean():.1f} calendar days")
    gross = (trades["net_pnl"] + trades["charges"]).sum()
    print(f"  Closed trades: profit before charges Rs {gross:,.2f}, charges Rs {trades['charges'].sum():,.2f}, "
          f"after charges Rs {trades['net_pnl'].sum():,.2f}")

    print("\n== Year by year")
    for year, value in result.performance.yearly_returns.items():
        print(f"  {year}: {value:7.2%}")

    # 2. By stock
    daily = pd.DataFrame({s: historify(s, "D")["close"] for s in BASKET})
    stocks = by_stock(result, daily)
    print("\n== By stock")
    print(stocks.to_string(formatters={
        "win_rate": "{:.0%}".format, "closed_pnl": "{:,.0f}".format, "open_pnl": "{:,.0f}".format,
        "total_pnl": "{:,.0f}".format, "charges": "{:,.0f}".format, "stock_return_buy_hold": "{:.1%}".format,
    }))

    # 3. Yardsticks: the same stocks held, and the NIFTY 50 held, over the same dates
    hold = bt.backtest(EqualWeightHold, client, **run)
    nifty = bt.backtest(NiftyBeesHold, client, **run)
    later = dict(run, start=str(began.date())) if began is not None else run
    hold_later = bt.backtest(EqualWeightHold, client, **later)
    nifty_later = bt.backtest(NiftyBeesHold, client, **later)
    keys = ["net_profit", "cagr", "max_drawdown", "volatility", "sharpe"]
    runs = {
        "Strategy 04 (Supertrend on the basket)": result,
        "Same 10 stocks, bought and held": hold,
        "NIFTYBEES, bought and held": nifty,
        f"Same 10 stocks, held from the first order ({later['start']})": hold_later,
        f"NIFTYBEES, held from the first order ({later['start']})": nifty_later,
    }
    table = pd.DataFrame({name: {k: r.metrics[k] for k in keys} for name, r in runs.items()}).T
    print("\n== Compared with holding")
    print(table.to_string(formatters={
        "net_profit": "{:,.2f}".format, "cagr": "{:.2%}".format, "max_drawdown": "{:.2%}".format,
        "volatility": "{:.2%}".format, "sharpe": "{:.2f}".format,
    }))

    # 4. Reality checks: worse fills and late orders
    print("\n== Reality checks (profit kept versus the backtest)")
    base_profit = result.metrics["net_profit"]
    for label, kwargs in (("Filled at the next candle's close", {"fill": "next_close"}),
                          ("Every order one candle late", {"delay_entries": 1, "delay_exits": 1})):
        profit = bt.backtest(SupertrendBasket, client, **run, **kwargs).metrics["net_profit"]
        kept = profit / base_profit if base_profit > 0 else float("nan")
        print(f"  {label:<34}: Rs {profit:,.2f} ({kept:.0%} kept)")

    # 5. Warnings
    print("\n== Warnings")
    for line in result.warnings:
        print("  -", line)

    # 6. Files
    columns = ["symbol", "entry_time", "exit_time", "quantity", "entry_price", "exit_price",
               "net_pnl", "return_pct", "bars_held", "days_held", "charges", "exit_reason"]
    trades[columns].to_csv(REPORTS / "trades.csv")
    stocks.to_csv(REPORTS / "by_stock.csv")
    table.to_csv(REPORTS / "compared.csv")
    save_signals(REPORTS / "signals.csv")
    result.to_csv(str(REPORTS / "tables"))
    result.tearsheet(str(REPORTS / "tearsheet.html"))
    def daily_value(series):
        """One value per day (the last one), so the charts stay small."""
        series = series.copy()
        series.index = pd.to_datetime(series.index).tz_localize(None).normalize()
        return series.groupby(level=0).last()

    curves = {
        "Strategy 04 (Supertrend on the basket)": (daily_value(result.equity["equity_rupees"]), BLUE),
        "Same 10 stocks, bought and held": (daily_value(hold.equity["equity_rupees"]), ORANGE),
        "NIFTYBEES, bought and held": (daily_value(nifty.equity["equity_rupees"]), AQUA),
    }
    write_report([equity_chart(curves), drawdown_chart(curves), stock_chart(stocks)], REPORTS / "strategy_report.html")
    print(f"\nSaved: {REPORTS / 'strategy_report.html'} (Plotly charts)")
    print(f"       {REPORTS / 'tearsheet.html'}, trades.csv, by_stock.csv, compared.csv, signals.csv, tables/")
