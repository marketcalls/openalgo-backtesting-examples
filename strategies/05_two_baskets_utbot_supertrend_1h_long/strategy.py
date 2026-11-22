"""
Strategy 05: two strategies on one Rs 10 lakh account, hourly candles, long only

Account   : Rs 10,00,000 in one account, split 60:40 between the two strategies.
            Each strategy trades only its own money (pool "shared": one account, and an
            order also needs the account's free cash).

Strategy A: UT Bot, 60 percent (Rs 6,00,000) on SBIN, RELIANCE, MAXHEALTH, CIPLA
  Idea      : the "UT Bot Strategy" Pine script (version 4, credited to HPotter). A
              trailing stop follows the close at a distance of key value x ATR. While the
              close stays above it, the stop only rises; while the close stays below it,
              the stop only falls; when the close crosses it, the stop restarts on the
              other side. A close crossing above the stop is a buy signal, a close
              crossing below it a sell signal.
  Settings  : key value 1, ATR period 10 (Wilder's average true range, as Pine's atr()),
              signals from ordinary candles (the script's Heikin Ashi option is off).
              The script's ema(src, 1) is the close itself, so buy is simply "the close
              crossed above the stop" and sell "the stop crossed above the close".
  Entry     : a buy signal at a candle's close while the stock is not held: BUY at
              MARKET, filled at the OPEN of the next candle.
  Exit      : a sell signal while the stock is held: SELL ALL at MARKET at the next
              candle's open. The script also opens a short on a sell; this version is
              long only, so a sell only closes the long.

Strategy B: Supertrend, 40 percent (Rs 4,00,000) on SUNPHARMA, ICICIBANK, TATASTEEL, MARUTI
  Indicator : Supertrend, ATR period 10, multiplier 3 (strategy 01's rules)
  Entry     : the Supertrend turns green (red to green) at a candle's close while the
              stock is not held: BUY at MARKET at the next candle's open.
  Exit      : the Supertrend is red at a candle's close while the stock is held: SELL
              ALL at MARKET at the next candle's open.

Both strategies
  Allocation: equal inside each strategy. Each buy is 23.75 percent of that strategy's
              money at the moment, in whole shares, so its four stocks held at once fill
              95 percent and 5 percent stays in cash for a gap up at the next open.
  Last candle of the day: a signal at the close of the day's last candle has no candle
              left that day, so its order is placed at 09:15 the next trading day and
              fills at that day's open. The last candle closes at 15:30 until 31 July 2026;
              from 3 August 2026 the data has no 15:15 candle, so the 14:15 candle is last.
  Direction : long only. No stop-loss or target beyond the signals.
  Product   : CNC (delivery), held overnight for as long as the signal lasts.
  Costs     : Indian delivery charges at each trade date's rates (zero delivery
              brokerage, STT, exchange charges, SEBI fee, stamp duty, GST, DP charge) and
              slippage of 2 basis points on every fill.
  Period    : 1 Apr 2022 to 20 Nov 2026. Historify's 1-minute candles start on 22 Nov 2021;
              the months before 1 Apr 2022 warm up the indicators, so both strategies
              can trade from the first day of the test.
  Benchmark : NIFTY 50 (daily closes from Historify).
  Data      : Historify on the OpenAlgo server (source="db"). The engine builds hourly
              candles from the 1-minute ones and fills each order at the open of the next
              1-minute candle, the same price as the next hourly candle's open.
  Note      : openalgo.ta has no UT Bot, and self.I takes only openalgo.ta functions, so the
              ATR comes from self.I(ta.atr, ...) and the trailing stop is worked out in
              on_bar from closed candles only (no look-ahead), with the same function
              that writes signals.csv.

Run       : python strategy.py   (from this folder, with the Python that has openalgo 2.4.0,
            the OpenAlgo server running and OPENALGO_API_KEY in the .env file of
            "backtesting examples"); then python charts.py for the candle charts.
Outputs   : printed report, and in reports/: trades.csv, signals.csv, by_stock.csv,
            compared.csv, trade_check.csv, tearsheet.html (the account),
            tearsheet_utbot.html, tearsheet_supertrend.html, strategy_report.html
            (Plotly) and every table of the run in tables/
"""
import math
import os
from datetime import date, time
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import openalgo.backtest as bt
from openalgo import api, ta

# Where things are
HERE = Path(__file__).resolve().parent
REPORTS = HERE / "reports"

# The test settings, shared by every run in this file
START = "2022-04-01"
END = "2026-11-20"
DATA_FROM = "2021-11-22"      # Historify's first candle: signals.csv starts here so the indicators match the engine's
CAPITAL = 10_00_000           # Rs 10 lakh for the whole account
SPLIT = {"UTBotBasket": 6_00_000, "SupertrendBasket": 4_00_000}  # 60:40 between the strategies
UT_STOCKS = ("SBIN", "RELIANCE", "MAXHEALTH", "CIPLA")
ST_STOCKS = ("SUNPHARMA", "ICICIBANK", "TATASTEEL", "MARUTI")
ALLOC_PCT = 23.75             # percent of a strategy's money per buy: 4 stocks x 23.75 = 95
NO_1515_CANDLE_FROM = date(2026, 8, 3)  # from this date the 14:15 candle is the day's last
DONE = {"Filled", "Rejected", "Cancelled", "Expired"}  # order states that are no longer waiting
LABEL = {"UTBotBasket": "UT Bot (60%)", "SupertrendBasket": "Supertrend (40%)"}


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


def last_candle_of_day(bar):
    """True for the day's last hourly candle: no candle follows it to fill an order today."""
    closes_at = bar.close_time.time()
    if bar.time.date() >= NO_1515_CANDLE_FROM:
        return closes_at >= time(15, 15)
    return closes_at >= time(15, 30)


# ---------------------------------------------------------------- the UT Bot, line by line of the Pine script
def ut_step(prev_stop, close, prev_close, n_loss):
    """One candle of the UT Bot trailing stop (xATRTrailingStop), as the Pine script computes it."""
    if math.isnan(n_loss):                      # the ATR is not ready yet
        return math.nan
    p = 0.0 if math.isnan(prev_stop) else prev_stop   # nz(xATRTrailingStop[1], 0)
    if close > p and prev_close > p:            # stayed above the stop: raise it, never lower it
        return max(p, close - n_loss)
    if close < p and prev_close < p:            # stayed below the stop: lower it, never raise it
        return min(p, close + n_loss)
    if close > p:                               # crossed above: restart the stop below the close
        return close - n_loss
    return close + n_loss                       # crossed below: restart it above the close


def ut_signals(prev_stop, stop, prev_close, close):
    """buy = crossover(close, stop), sell = crossover(stop, close); False while a value is missing."""
    buy = close > stop and prev_close <= prev_stop
    sell = stop > close and prev_stop <= prev_close
    return buy, sell


def ut_bot(close, atr, key_value):
    """The UT Bot stop and its buy and sell signals over a whole series of closes."""
    close = np.asarray(close, dtype=float)
    n_loss = key_value * np.asarray(atr, dtype=float)
    stop = np.full(len(close), np.nan)
    buy = np.zeros(len(close), dtype=bool)
    sell = np.zeros(len(close), dtype=bool)
    prev_stop = prev_close = math.nan
    for i in range(len(close)):
        stop[i] = ut_step(prev_stop, close[i], prev_close, n_loss[i])
        buy[i], sell[i] = ut_signals(prev_stop, stop[i], prev_close, close[i])
        prev_stop, prev_close = stop[i], close[i]
    return stop, buy, sell


# ---------------------------------------------------------------- the two strategies
class BasketBase(bt.Strategy):
    """What both strategies share: the 09:15 timer for last-candle signals, and trading each
    stock towards what its signal wants."""
    exchange, interval = "NSE", "1h"
    product = "CNC"           # delivery: hold overnight (hourly candles would otherwise trade MIS)
    alloc_pct = ALLOC_PCT

    def on_bar(self, bars):
        want = self.state.setdefault("want", {})
        for s in bars:
            wish = self.wish(s)
            if wish:
                want[s] = wish
        # The day's last candle: the market has closed, so the 09:15 timer acts tomorrow.
        if any(last_candle_of_day(bar) for bar in bars.values()):
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


class UTBotBasket(BasketBase):
    symbols = UT_STOCKS
    key_value = 1.0   # 'a' in the script: the stop sits key_value x ATR from the close
    atr_period = 10   # 'c' in the script

    # init: one ATR per stock, the trailing stop's memory and the 09:15 timer.
    def init(self):
        self.atr = {}
        for s in self.symbols:
            d = self.data[s]
            self.atr[s] = self.I(ta.atr, d.high, d.low, d.close, self.atr_period)
        self.trail = {}       # per stock: [candles worked out, last stop, last close]
        self.last_order = {}  # per stock: the last order sent
        self.at("09:15", self.at_open)

    def wish(self, s):
        """Bring the stock's stop up to the candle that just closed: "long" after a buy
        signal, "flat" after a sell signal, None when neither happened."""
        closes, atr = self.data[s].close, self.atr[s]
        n = len(closes)
        if s not in self.trail:
            # First decision for this stock: work the stop out over every closed candle,
            # the history before the start included, as a chart does from its first candle.
            c = closes.values
            stop, buy, sell = ut_bot(c, atr.values, self.key_value)
            self.trail[s] = [n, stop[-1], c[-1]]
            return "long" if buy[-1] else "flat" if sell[-1] else None
        worked, prev_stop, prev_close = self.trail[s]
        wish = None
        for k in range(n - worked, 0, -1):  # every candle closed since the last call, oldest first
            close = closes[-k]
            stop = ut_step(prev_stop, close, prev_close, self.key_value * atr[-k])
            buy, sell = ut_signals(prev_stop, stop, prev_close, close)
            if buy:
                wish = "long"
            elif sell:
                wish = "flat"
            prev_stop, prev_close = stop, close
        self.trail[s] = [n, prev_stop, prev_close]
        return wish


class SupertrendBasket(BasketBase):
    symbols = ST_STOCKS
    period = 10        # ATR period of the Supertrend
    multiplier = 3.0   # distance of the line from the price, in ATRs

    # init: one Supertrend per stock and the 09:15 timer.
    def init(self):
        self.direction = {}  # per stock: -1 = green (uptrend), 1 = red (downtrend)
        for s in self.symbols:
            d = self.data[s]
            _line, self.direction[s] = self.I(ta.supertrend, d.high, d.low, d.close,
                                              self.period, self.multiplier)
        self.last_order = {}
        self.at("09:15", self.at_open)

    def wish(self, s):
        if self.direction[s].crossed_below(0):  # turned green on this candle
            return "long"
        if self.direction[s][-1] > 0:            # red on this candle
            return "flat"
        return None


# ---------------------------------------------------------------- yardsticks
class HoldUTStocks(bt.Strategy):
    """The UT Bot's four stocks, bought on day one with the same Rs 6 lakh and held."""
    symbols, exchange, interval = UT_STOCKS, "NSE", "D"

    def on_bar(self, bars):
        if not self.state.get("invested"):
            self.state["invested"] = True
            self.rebalance({s: 25 for s in self.symbols}, cash_buffer=5)


class HoldSTStocks(HoldUTStocks):
    """The Supertrend's four stocks, bought on day one with the same Rs 4 lakh and held."""
    symbols = ST_STOCKS


class NiftyBeesHold(bt.Strategy):
    """The NIFTY 50 itself (NIFTYBEES), 95 percent of Rs 10 lakh bought on day one and held."""
    symbol, exchange, interval = "NIFTYBEES", "NSE", "D"

    def on_bar(self, bar):
        if self.position.is_flat:
            self.buy(size=bt.size.percent(95))


# ---------------------------------------------------------------- reading the results
def headline(r):
    """The figures a trader reads first, for one strategy or for the whole account."""
    m = r.metrics
    trades = r.trade_list()
    wins = trades[trades["net_pnl"] > 0]
    losses = trades[trades["net_pnl"] <= 0]
    gross = (trades["net_pnl"] + trades["charges"]).sum()
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
        "Gross profit, closed (Rs)": gross,
        "Charges (Rs)": r.costs["charged"].sum(),
        "Charges / gross": trades["charges"].sum() / gross if gross > 0 else float("nan"),
        "Slippage (Rs)": r.fills["slippage_rupees"].sum(),
    }


def show(title, figures):
    print(f"\n== {title}")
    for name, value in figures.items():
        if "(Rs)" in name:
            print(f"  {name:<26}: {value:,.2f}")
        elif name == "Closed trades":
            print(f"  {name:<26}: {value}")
        elif name in ("Sharpe ratio", "Profit factor"):
            print(f"  {name:<26}: {value:.2f}")
        else:
            print(f"  {name:<26}: {value:.2%}")


def historify(symbol, interval, start=DATA_FROM, exchange="NSE"):
    bars = client.history(symbol=symbol, exchange=exchange, interval=interval,
                          start_date=start, end_date=END, source="db")
    if not hasattr(bars, "index") or len(bars) == 0:
        raise SystemExit(f"Historify returned no {interval} candles for {symbol}: {bars}")
    return bars


def build_signals():
    """Every hourly candle of every stock from Historify, with its indicator worked out
    again from the raw candles, the signal and what the strategy wants after it."""
    frames = []
    for s in UT_STOCKS + ST_STOCKS:
        bars = historify(s, "1h")
        f = bars[["open", "high", "low", "close"]].copy()
        if s in UT_STOCKS:
            atr = ta.atr(bars["high"], bars["low"], bars["close"], UTBotBasket.atr_period)
            stop, buy, sell = ut_bot(bars["close"], atr, UTBotBasket.key_value)
            f.insert(0, "strategy", "UTBotBasket")
            f["line"] = np.round(stop, 2)
            f["side"] = np.where(bars["close"] > stop, "above", "below")
            f["signal"] = np.where(buy, "buy", np.where(sell, "sell", ""))
            f["want"] = np.where(buy, "long", np.where(sell, "flat", ""))
        else:
            line, direction = ta.supertrend(bars["high"], bars["low"], bars["close"],
                                            SupertrendBasket.period, SupertrendBasket.multiplier)
            prev = direction.shift(1)
            green_flip = (prev == 1) & (direction == -1)
            red_flip = (prev == -1) & (direction == 1)
            f.insert(0, "strategy", "SupertrendBasket")
            f["line"] = line.round(2)
            f["side"] = direction.map({-1: "green", 1: "red"})
            f["signal"] = np.where(green_flip, "buy", np.where(red_flip, "sell", ""))
            f["want"] = np.where(green_flip, "long", np.where(direction == 1, "flat", ""))
        f.insert(1, "symbol", s)
        frames.append(f)
    signals = pd.concat(frames)
    signals.index.name = "time"
    return signals


def expected_trades(signals):
    """Replay the rules on the recomputed signals: decisions from the first candle of the
    test, each fill at the open of the candle after the decision (09:15 the next day for
    the day's last candle)."""
    rows = []
    for s, f in signals.groupby("symbol", sort=False):
        times = f.index
        wants = f["want"].to_numpy()
        live = times >= pd.Timestamp(START, tz=times.tz)
        want, entry = None, None
        for i in range(len(f) - 1):
            if not live[i]:
                continue
            if wants[i]:
                want = wants[i]
            if want == "long" and entry is None:
                entry = times[i + 1]
            elif want == "flat" and entry is not None:
                rows.append((s, entry, times[i + 1]))
                entry = None
        if entry is not None:
            rows.append((s, entry, pd.NaT))
    return pd.DataFrame(rows, columns=["symbol", "entry_time", "exit_time"])


def check_trades(result, signals):
    """Each engine trade against the replay: same entry and exit candles, stock by stock."""
    want = expected_trades(signals)
    got = result.trade_list()[["symbol", "entry_time", "exit_time"]].copy()
    still = result.final_positions
    held = still[still["quantity_units"] != 0] if len(still) else still
    open_rows = []
    for s in held["symbol"] if len(held) else []:
        entries = result.fills[(result.fills["symbol"] == s) & (result.fills["side"] == "BUY")]
        open_rows.append({"symbol": s, "entry_time": pd.Timestamp(entries["time"].max()), "exit_time": pd.NaT})
    if open_rows:
        got = pd.concat([got, pd.DataFrame(open_rows)], ignore_index=True)
    for frame in (want, got):
        for col in ("entry_time", "exit_time"):
            frame[col] = pd.to_datetime(frame[col], utc=True).dt.tz_convert("Asia/Kolkata")
    merged = want.merge(got, on=["symbol", "entry_time"], how="outer",
                        suffixes=("_expected", "_engine"), indicator=True)
    merged["exit_matches"] = (merged["exit_time_expected"] == merged["exit_time_engine"]) | (
        merged["exit_time_expected"].isna() & merged["exit_time_engine"].isna())
    # An expected entry whose order the engine rejected (not enough free cash): the strategy
    # keeps wanting the stock and buys at a later candle, so the replay and the engine differ.
    orders = result.orders
    refused = orders[orders["status"] == "Rejected"]
    refused_at = set(zip(refused["symbol"],
                         pd.to_datetime(refused["decided_at"], utc=True).dt.tz_convert("Asia/Kolkata")))
    merged["order_rejected_here"] = [(s, t) in refused_at for s, t in zip(merged["symbol"], merged["entry_time"])]
    return merged.sort_values(["symbol", "entry_time"])


def by_stock(result, daily_closes):
    """Each stock's trades and profit in its strategy, beside the stock's own return."""
    trades = result.trade_list()
    held = result.final_positions
    held = held.set_index("symbol") if len(held) else pd.DataFrame()
    rows = []
    for s in UT_STOCKS + ST_STOCKS:
        t = trades[trades["symbol"] == s]
        open_pnl = float(held.loc[s, "unrealized_rupees"]) if s in held.index else 0.0
        closes = daily_closes[s].dropna()
        rows.append({
            "symbol": s,
            "strategy": "UT Bot" if s in UT_STOCKS else "Supertrend",
            "closed_trades": len(t),
            "win_rate": (t["net_pnl"] > 0).mean() if len(t) else float("nan"),
            "closed_pnl": t["net_pnl"].sum(),
            "open_pnl": open_pnl,
            "total_pnl": t["net_pnl"].sum() + open_pnl,
            "charges": t["charges"].sum(),
            "stock_return_buy_hold": closes.iloc[-1] / closes.iloc[0] - 1,
        })
    return pd.DataFrame(rows).set_index("symbol")


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


def daily_value(series):
    """One value per day (the last one), so the charts stay small."""
    series = series.copy()
    index = pd.to_datetime(series.index)
    if index.tz is not None:
        index = index.tz_convert("Asia/Kolkata").tz_localize(None)
    series.index = index.normalize()
    return series.groupby(level=0).last()


def equity_chart(curves, title, subtitle, base):
    fig = go.Figure()
    for name, (series, colour) in curves.items():
        fig.add_trace(go.Scatter(x=series.index, y=series.values, name=name, mode="lines",
                                 line=dict(color=colour, width=2),
                                 hovertemplate=name + "<br>%{x|%d %b %Y}: Rs %{y:,.0f}<extra></extra>"))
        fig.add_annotation(x=series.index[-1], y=series.values[-1], xanchor="left", xshift=6, showarrow=False,
                           text=f"{name.split(' (')[0]}<br>Rs {series.values[-1] / 1e5:,.2f} lakh",
                           font=dict(color=INK_2, size=11), align="left")
    fig.add_hline(y=base, line=dict(color=AXIS, width=1))
    layout(fig, title, subtitle, 480)
    fig.update_yaxes(title=dict(text="account value (Rs)", font=dict(color=MUTED)), tickformat=",.0f")
    fig.update_layout(hovermode="x unified")
    return fig


def drawdown_chart(curves):
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
    t = table.sort_values("total_pnl")
    colours = [BLUE if v >= 0 else RED for v in t["total_pnl"]]
    labels = [f"{s} ({row.strategy})" for s, row in t.iterrows()]
    fig = go.Figure(go.Bar(
        x=t["total_pnl"], y=labels, orientation="h", marker=dict(color=colours),
        text=[f"Rs {v:,.0f}" for v in t["total_pnl"]], textposition="outside", cliponaxis=False,
        textfont=dict(color=INK_2),
        customdata=t[["closed_trades", "closed_pnl", "open_pnl", "stock_return_buy_hold"]].values,
        hovertemplate=("%{y}<br>profit Rs %{x:,.0f}<br>%{customdata[0]} closed trades, Rs %{customdata[1]:,.0f}"
                       "<br>still held: Rs %{customdata[2]:,.0f}<br>the stock itself: %{customdata[3]:.1%}<extra></extra>"),
    ))
    layout(fig, "Profit by stock", "Closed trades plus any position still held on the last day, after charges.",
           420, left=190)
    fig.update_layout(barcornerradius=4, bargap=0.35, showlegend=False)
    fig.update_xaxes(title=dict(text="profit (Rs)", font=dict(color=MUTED)), tickformat=",.0f")
    fig.update_yaxes(showgrid=False, tickfont=dict(color=INK_2))
    return fig


def write_report(figures, path):
    parts = [f"<html><head><meta charset='utf-8'><title>Strategy 05 report</title><style>body{{background:{SURFACE};"
             f"color:{INK};font-family:{FONT};max-width:1100px;margin:24px auto;padding:0 16px}}"
             f".chart{{margin:24px 0 40px}}</style></head><body><h1 style='font-size:24px'>Strategy 05: "
             f"UT Bot (60%) and Supertrend (40%) on one Rs 10 lakh account</h1>"]
    for i, fig in enumerate(figures):
        parts.append("<div class='chart'>" + fig.to_html(full_html=False, include_plotlyjs=(i == 0),
                                                       config={"displaylogo": False}) + "</div>")
    parts.append("</body></html>")
    path.write_text("".join(parts), encoding="utf-8")


# ---------------------------------------------------------------- the run
if __name__ == "__main__":
    REPORTS.mkdir(exist_ok=True)
    # Every run reads Historify (source="db"); market orders fill at the next candle's open.
    run = dict(start=START, end=END, source="db", benchmark="NIFTY")
    STRATEGIES = [UTBotBasket, SupertrendBasket]

    # 1. The two strategies together on one account
    result = bt.backtest(STRATEGIES, client, capital=SPLIT, **run)
    print(result.summary())
    show("The account: both strategies, Rs 10 lakh", headline(result))
    for name in SPLIT:
        r = result.strategy(name)
        show(f"{LABEL[name]} on its own Rs {SPLIT[name]:,} ", headline(r))
        t = r.trade_list()
        print("  How the trades ended  :", t["exit_reason"].value_counts().to_dict())
        print(f"  Average holding       : {t['bars_held'].mean():.1f} hourly candles, {t['days_held'].mean():.1f} calendar days")
        print(f"  NIFTY over the test   : {r.metrics['benchmark_total_return']:.2%}   beta {r.metrics['beta']:.2f}")
        top = t["net_pnl"].nlargest(3).sum()
        print(f"  Best 3 trades         : Rs {top:,.2f} ({top / t['net_pnl'].sum():.0%} of the closed profit)"
              if t["net_pnl"].sum() > 0 else f"  Best 3 trades         : Rs {top:,.2f}")
        print(f"  Average MFE / MAE     : Rs {t['mfe'].mean():,.0f} / Rs {t['mae'].mean():,.0f} per trade "
              f"(average net Rs {t['net_pnl'].mean():,.0f})")
        print("  Year by year          :", ", ".join(f"{y} {v:.2%}" for y, v in r.performance.yearly_returns.items()))
    print("\n== The account, year by year")
    for year, value in result.performance.yearly_returns.items():
        print(f"  {year}: {value:7.2%}")
    print("\n== Correlation of the two strategies' daily returns")
    print(result.correlation.round(2).to_string())
    print("\n== Each strategy's part in the account")
    print(result.contribution.to_string())

    # 2. By stock
    daily = pd.DataFrame({s: historify(s, "D", start=START)["close"] for s in UT_STOCKS + ST_STOCKS})
    stocks = by_stock(result, daily)
    print("\n== By stock")
    print(stocks.to_string(formatters={
        "win_rate": "{:.0%}".format, "closed_pnl": "{:,.0f}".format, "open_pnl": "{:,.0f}".format,
        "total_pnl": "{:,.0f}".format, "charges": "{:,.0f}".format, "stock_return_buy_hold": "{:.1%}".format,
    }))

    # 3. Yardsticks: the same stocks with the same 60:40 money held, and NIFTYBEES held
    hold = bt.backtest([HoldUTStocks, HoldSTStocks], client,
                       capital={"HoldUTStocks": SPLIT["UTBotBasket"], "HoldSTStocks": SPLIT["SupertrendBasket"]},
                       **run)
    nifty = bt.backtest(NiftyBeesHold, client, capital=CAPITAL, **run)
    keys = ["net_profit", "total_return", "cagr", "max_drawdown", "volatility", "sharpe"]
    runs = {
        "Strategy 05 account (UT Bot 60% + Supertrend 40%)": result,
        "  UT Bot on Rs 6 lakh": result.strategy("UTBotBasket"),
        "  Supertrend on Rs 4 lakh": result.strategy("SupertrendBasket"),
        "Same 8 stocks, same 60:40 money, bought and held": hold,
        "  UT Bot's 4 stocks held, Rs 6 lakh": hold.strategy("HoldUTStocks"),
        "  Supertrend's 4 stocks held, Rs 4 lakh": hold.strategy("HoldSTStocks"),
        "NIFTYBEES, Rs 10 lakh bought and held": nifty,
    }
    table = pd.DataFrame({name: {k: r.metrics[k] for k in keys} for name, r in runs.items()}).T
    print("\n== Compared with holding")
    print(table.to_string(formatters={
        "net_profit": "{:,.2f}".format, "total_return": "{:.2%}".format, "cagr": "{:.2%}".format,
        "max_drawdown": "{:.2%}".format, "volatility": "{:.2%}".format, "sharpe": "{:.2f}".format,
    }))

    # 4. Reality checks: worse fills and late orders, for the account and each strategy
    print("\n== Reality checks (net profit, and the share of the backtest's kept)")
    base = {"account": result.metrics["net_profit"],
            **{name: result.strategy(name).metrics["net_profit"] for name in SPLIT}}
    for label, kwargs in (("Filled at the next candle's close", {"fill": "next_close"}),
                          ("Every order one candle late", {"delay_entries": 1, "delay_exits": 1})):
        check = bt.backtest(STRATEGIES, client, capital=SPLIT, **run, **kwargs)
        got = {"account": check.metrics["net_profit"],
               **{name: check.strategy(name).metrics["net_profit"] for name in SPLIT}}
        parts = []
        for key, profit in got.items():
            kept = f"{profit / base[key]:.0%} kept" if base[key] > 0 else "the backtest lost money"
            parts.append(f"{LABEL.get(key, 'account')} Rs {profit:,.0f} ({kept})")
        print(f"  {label:<34}: " + " | ".join(parts))

    # 5. Warnings
    print("\n== Warnings")
    for line in result.warnings:
        print("  -", line)

    # 6. Cross-check: the engine's trades against the rules replayed on recomputed signals
    signals = build_signals()
    checked = check_trades(result, signals)
    both = checked["_merge"] == "both"
    print("\n== Cross-check against the indicators worked out again from Historify's candles")
    print(f"  Trades in both          : {both.sum()} (exit on the same candle: {checked.loc[both, 'exit_matches'].sum()})")
    replay_only = checked["_merge"] == "left_only"
    print(f"  Only in the replay      : {replay_only.sum()} "
          f"({(replay_only & checked['order_rejected_here']).sum()} of them an order the engine rejected for cash)")
    print(f"  Only in the engine      : {(checked['_merge'] == 'right_only').sum()} (the later buy after such a rejection, "
          "or a special session whose hourly candles start off the 09:15 grid)")
    odd = checked[replay_only & ~checked["order_rejected_here"]]
    if len(odd):
        print("  Replay entries not explained by a rejected order:")
        print(odd.head(20).to_string(index=False))

    # 7. Files
    trades = result.trade_list()
    columns = ["strategy", "symbol", "entry_time", "exit_time", "quantity", "entry_price", "exit_price",
               "net_pnl", "return_pct", "bars_held", "days_held", "charges", "mae", "mfe", "exit_reason"]
    trades[[c for c in columns if c in trades.columns]].to_csv(REPORTS / "trades.csv")
    result.final_positions.to_csv(REPORTS / "open_positions.csv", index=False)
    signals[signals.index >= pd.Timestamp(START, tz="Asia/Kolkata")].to_csv(REPORTS / "signals.csv")
    stocks.to_csv(REPORTS / "by_stock.csv")
    table.to_csv(REPORTS / "compared.csv")
    checked.drop(columns="_merge").assign(found_in=checked["_merge"].astype(str)).to_csv(
        REPORTS / "trade_check.csv", index=False)
    result.to_csv(str(REPORTS / "tables"))
    result.tearsheet(str(REPORTS / "tearsheet.html"))
    result.strategy("UTBotBasket").tearsheet(str(REPORTS / "tearsheet_utbot.html"))
    result.strategy("SupertrendBasket").tearsheet(str(REPORTS / "tearsheet_supertrend.html"))

    curves = {
        "Strategy 05 (both strategies)": (daily_value(result.equity), BLUE),
        "Same 8 stocks held (60:40)": (daily_value(hold.equity), ORANGE),
        "NIFTYBEES held": (daily_value(nifty.equity["equity_rupees"]), AQUA),
    }
    write_report([
        equity_chart(curves, "Account value, Rs 10 lakh invested three ways",
                     f"{START} to {END}. The grey line is the starting Rs 10 lakh.", CAPITAL),
        drawdown_chart(curves),
        stock_chart(stocks),
    ], REPORTS / "strategy_report.html")
    print(f"\nSaved in {REPORTS}: strategy_report.html, tearsheet.html, tearsheet_utbot.html, "
          "tearsheet_supertrend.html, trades.csv, open_positions.csv, signals.csv, by_stock.csv, "
          "compared.csv, trade_check.csv, tables/")
