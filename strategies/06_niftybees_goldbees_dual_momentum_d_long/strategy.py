"""
Strategy 06: Momentum switch between NIFTYBEES and GOLDBEES, checked every quarter,
             with a 200-day EMA entry filter
             (Antonacci's dual momentum with the crash filter removed)

Idea      : Gary Antonacci, "Risk Premia Harvesting Through Dual Momentum" (2012, revised
            2013): Faber's relative strength plus a crash filter. Once a quarter, pick
            whichever of NIFTYBEES and GOLDBEES rose more over the lookback (relative
            momentum). The paper's crash filter (hold cash unless the winner's rise beat a
            safe FD-like return of 6 percent a year) was tested first and then removed at
            the user's request: on the 12-month lookback it never acted, and on the 3-month
            lookback it cut the return from 11.83 to 9.26 percent a year. It stays in the
            comparison as mode="dual".
EMA filter: (added at the user's request) the pick is held only while its daily close is
            above its 200-day EMA. No buy starts while the close is below it: the strategy
            waits in cash and looks again at every day's close, buying at the next open
            after the first close above the EMA, unless the next quarterly check picks the
            other ETF. While holding, a daily close below the EMA sells at the next open,
            and the strategy waits in cash the same way. A switch still sells the old ETF
            (momentum says it is now the weaker one).
            The EMA is openalgo.ta.ema(close, 200) on every Historify daily candle from
            22 Nov 2016, as a chart draws it. The engine's own self.I EMA would wait for
            2,048 bars (8.3 years) of history; from 1 Jan 2018 this EMA is within 0.16
            percent of one started in 2008, and never on the other side of the price.
Market    : NIFTYBEES and GOLDBEES, NSE cash market (ETFs), daily candles, CNC (delivery).
Check     : the engine's quarterly timer (self.every("quarter")): the decision uses the
            close of the first session of January, April, July and October, and its orders
            fill at the next session's open.
Momentum  : each ETF's return over the lookback, from openalgo.ta.roc on its daily closes.
            One month is 247 / 12 sessions (NSE averaged 247 sessions a year from 2015 to
            2025), so 12 months = 247 sessions and 3 months = 62 sessions.
Crash     : (comparison runs only) the FD hurdle is 6 percent a year, about what a bank FD or
filter      a 91-day T-bill paid on average over the test; over a lookback of m months it
            is 1.06^(m/12) - 1 (6.00 percent for 12 months, 1.47 percent for 3 months).
            Cash earns nothing in the engine; the report estimates the FD interest.
Trades    : only when the choice changes. A switch from one ETF to the other sells at the
            first open and buys at the next session's open, once the sale money is in the
            account (from Dec 2020 to Oct 2024 only 80 percent of a sale could be used the
            same day). If a buy is ever refused, the strategy tries again the next day.
Sizing    : 95 percent of the account in the chosen ETF. The other 5 percent stays as cash,
            because daily ETF opening prices can be stray (see the stray-open check).
Compared  : the 3-month lookback (asked for) against the 12-month one; without the EMA
            filter, and with the EMA for entries only (no EMA exit); 6 and 9 months
            and monthly checks (looked at, not tuned); with the crash filter at 6 and 0
            percent, and the crash filter only (half in each ETF that beats the hurdle);
            NIFTYBEES held, GOLDBEES held, 60:40 held, 50:50 reset every quarter; and the
            NIFTY 50 index as the benchmark.
Period    : 1 Jan 2018 to 20 Nov 2026. Historify's daily candles start on 22 Nov 2016, and
            the 12-month lookback needs the first year.
Capital   : Rs 10,00,000. Charges: the zerodha preset (delivery). Its dated rates start on
            1 Jul 2020, so trades before that are charged at the 1 Jul 2020 rates
            (CostModel(backfill=True)); delivery STT was 0.1 percent on both sides then too.
            The engine charges ETFs like shares (0.1 percent STT), which overstates their
            real STT. Slippage: the default 2 basis points. Fills: the next open.
Data      : Historify on your OpenAlgo server (source="db"), daily candles.
Run       : python strategy.py   (from this folder; needs openalgo 2.4.0 or later, the
            OpenAlgo server running, and OPENALGO_API_KEY in the .env file of
            "backtesting examples")
Outputs   : printed report, and in reports/: strategy_report.html, tearsheet.html,
            tearsheet_3m.html, trades.csv, trades_3m.csv, signals.csv, compared.csv,
            rolling_returns.csv, trade_check.csv, stray_opens.csv and tables/
"""
import math
import os
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
START = "2018-01-01"
END = "2026-11-20"
DATA_FROM = "2016-11-22"      # first daily candle in Historify
CAPITAL = 10_00_000           # Rs 10 lakh
ETFS = ("NIFTYBEES", "GOLDBEES")
SESSIONS_PER_YEAR = 247       # NSE average, 2015 to 2025
FD_PCT = 6.0                  # the safe return the (removed) crash filter asks the winner to beat, percent a year
EMA_DAYS = 200                # the trend filter: no buy while the close is below this EMA
IST = "Asia/Kolkata"


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


def lookback_sessions(months):
    """Trading sessions in a lookback of `months` months."""
    return round(SESSIONS_PER_YEAR * months / 12)


def hurdle_over(months, pct_a_year):
    """The FD return over `months` months, in percent (the unit ta.roc gives)."""
    return ((1 + pct_a_year / 100) ** (months / 12) - 1) * 100


_EMA_TABLES = {}


def ema_table(symbol):
    """Each daily close of an ETF and its 200-day EMA, from every Historify candle (from
    22 Nov 2016), indexed by the candle's close time (15:30 IST), so a decision can take
    the last row closed before it and never a later one."""
    if symbol not in _EMA_TABLES:
        close = historify(symbol)["close"]
        table = pd.DataFrame({"close": close.to_numpy(), "ema": ta.ema(close.to_numpy(), EMA_DAYS)},
                             index=(close.index + pd.Timedelta(hours=15, minutes=30)).tz_localize(IST))
        _EMA_TABLES[symbol] = table
    return _EMA_TABLES[symbol]


def close_above_ema(symbol, when):
    """True when the ETF's last daily close at or before `when` is above its 200-day EMA."""
    table = ema_table(symbol)
    row = table[table.index <= when]
    if row.empty or math.isnan(row["ema"].iloc[-1]):
        return False
    return bool(row["close"].iloc[-1] > row["ema"].iloc[-1])


# ---------------------------------------------------------------- the strategy
class Momentum(bt.Strategy):
    symbols, exchange, interval = ETFS, "NSE", "D"
    product = "CNC"             # delivery: the ETF is held for months
    lookback_months = 12        # momentum is the return over this many months
    check_every = "quarter"     # "quarter" (asked for) or "month" (the paper)
    mode = "relative"           # "relative": always hold the stronger ETF (the crash filter removed);
                                # "dual": the paper, cash unless the winner beats the FD hurdle;
                                # "absolute": the crash filter only, half in each ETF that beats it
    hurdle_pct = FD_PCT         # the crash filter's FD-like return a year (modes "dual" and "absolute")
    ema_filter = "daily"        # "daily": hold only while the daily close is above the 200-day EMA
                                # (no buy below it, sell on a close below it); "entry": no buy below
                                # it, but no EMA exit; "off": no EMA filter
    invest_pct = 95             # percent of the account put in the chosen ETF

    def ema_allows(self, symbol):
        """The EMA filter on the last closed daily candle: may a buy of this ETF start now?"""
        return self.ema_filter == "off" or close_above_ema(symbol, self.now)

    # init: one rate-of-change line per ETF and the quarterly check.
    def init(self):
        sessions = lookback_sessions(self.lookback_months)
        self.momentum = {s: self.I(ta.roc, self.data[s].close, sessions) for s in self.symbols}
        self.every(self.check_every, self.check)

    # The check: runs for the close of the first session of each quarter; its orders fill
    # at the next session's open.
    def check(self):
        returns = {s: float(self.momentum[s][-1]) for s in self.symbols}
        if any(math.isnan(v) for v in returns.values()):
            return
        bar = hurdle_over(self.lookback_months, self.hurdle_pct)
        if self.mode == "absolute":
            # Crash filter only: half the account in each ETF that beats the FD return.
            passing = {s: 50 for s in self.symbols if returns[s] > bar}
            self.state["want"] = "+".join(passing) or "CASH"
            self.rebalance(passing, cash_buffer=100 - self.invest_pct)
            return
        best = max(self.symbols, key=lambda s: returns[s])            # relative momentum
        beats_fd = returns[best] > bar                                 # absolute momentum
        want = best if (beats_fd or self.mode == "relative") else "CASH"
        self.state["want"] = want
        # The EMA filter as it stands on the check's own candle
        self.state["cleared"] = want != "CASH" and self.ema_allows(want)
        held = [s for s in self.symbols if not self.positions[s].is_flat]
        for s in held:
            if s != want:
                self.exit(symbol=s)                                    # sell what is no longer wanted
        if want != "CASH" and not held and self.state["cleared"]:
            self.buy(symbol=want, size=bt.size.percent(self.invest_pct))
        # After a switch the buy waits for on_bar, when the sale money is in the account.

    # on_bar runs at every day's close. With the EMA exit, sell what is held after a close
    # below its 200-day EMA. Otherwise buy the wanted ETF once nothing is held and the EMA
    # allows it (the second half of a switch, a retry after a refused buy, or the first
    # close above the EMA after waiting in cash).
    def on_bar(self, bars):
        if self.mode == "absolute" or self.orders:
            return
        held = [s for s in self.symbols if not self.positions[s].is_flat]
        if self.ema_filter == "daily":
            below = [s for s in held if not close_above_ema(s, self.now)]
            for s in below:
                self.exit(symbol=s)                                    # closed below its 200-day EMA
            if below:
                return
        want = self.state.get("want", "CASH")
        if want != "CASH" and not held and self.ema_allows(want):
            self.buy(symbol=want, size=bt.size.percent(self.invest_pct))


class HoldMix(bt.Strategy):
    """Yardstick: NIFTYBEES and GOLDBEES bought on the first day in a fixed mix, either held
    (reset_every = "never") or reset to the mix at the first session of every quarter."""
    symbols, exchange, interval = ETFS, "NSE", "D"
    nifty_pct = 60
    reset_every = "never"   # "never" or "quarter"

    def on_bar(self, bars):
        quarter = (self.now.year, (self.now.month - 1) // 3)
        first = "quarter" not in self.state
        if first or (self.reset_every == "quarter" and quarter != self.state["quarter"]):
            self.state["quarter"] = quarter
            weights = {"NIFTYBEES": self.nifty_pct, "GOLDBEES": 100 - self.nifty_pct}
            self.rebalance({s: w for s, w in weights.items() if w > 0}, cash_buffer=5)


# ---------------------------------------------------------------- reading the results
def historify(symbol, start=DATA_FROM, exchange="NSE"):
    """Daily candles from Historify, indexed by date."""
    bars = client.history(symbol=symbol, exchange=exchange, interval="D",
                          start_date=start, end_date=END, source="db")
    if not hasattr(bars, "index") or len(bars) == 0:
        raise SystemExit(f"Historify returned no daily candles for {symbol}: {bars}")
    bars.index = pd.DatetimeIndex(bars.index).normalize()
    return bars


def daily_value(series):
    """One value per day (the last one), indexed by date without time zone."""
    series = series.copy()
    index = pd.to_datetime(series.index)
    if index.tz is not None:
        index = index.tz_convert(IST).tz_localize(None)
    series.index = index.normalize()
    return series.groupby(level=0).last()


def equity_of(r):
    return daily_value(r.equity["equity_rupees"])


def holdings_by_day(r, sessions):
    """What the account held after each session's fills: an ETF, both, or cash."""
    fills = r.fills.copy()
    fills["day"] = pd.to_datetime(fills["time"]).dt.tz_convert(IST).dt.tz_localize(None).dt.normalize()
    fills["signed"] = np.where(fills["side"] == "BUY", 1, -1) * fills["quantity_units"]
    units = fills.pivot_table(index="day", columns="symbol", values="signed", aggfunc="sum")
    units = units.reindex(columns=list(ETFS), fill_value=0).reindex(sessions).fillna(0).cumsum()
    held = units > 0
    label = np.where(held.all(axis=1), "both",
                     np.where(held["NIFTYBEES"], "NIFTYBEES", np.where(held["GOLDBEES"], "GOLDBEES", "cash")))
    return pd.Series(label, index=sessions)


def headline(r, sessions):
    """The figures a trader reads first."""
    m = r.metrics
    trades = r.trade_list()
    gross = trades["gross_pnl"].sum()
    held = holdings_by_day(r, sessions)
    years = (pd.Timestamp(END) - pd.Timestamp(START)).days / 365.25
    return {
        "Net profit (Rs)": m["net_profit"],
        "Return": m["total_return"],
        "CAGR": m["cagr"],
        "Max drawdown": m["max_drawdown"],
        "Volatility (yearly)": m["volatility"],
        "Sharpe ratio": m["sharpe"],
        "Closed trades": len(trades),
        "Switches a year": len(trades) / years,
        "Win rate": (trades["net_pnl"] > 0).mean() if len(trades) else float("nan"),
        "Days in NIFTYBEES": (held == "NIFTYBEES").mean(),
        "Days in GOLDBEES": (held == "GOLDBEES").mean(),
        "Days in cash": (held == "cash").mean(),
        "Charges (Rs)": r.costs["charged"].sum(),
        "Charges / gross, closed": trades["charges"].sum() / gross if gross > 0 else float("nan"),
    }


def show(title, figures):
    print(f"\n== {title}")
    for name, value in figures.items():
        if "(Rs)" in name:
            print(f"  {name:<26}: {value:,.2f}")
        elif name in ("Closed trades",):
            print(f"  {name:<26}: {value}")
        elif name in ("Sharpe ratio", "Switches a year"):
            print(f"  {name:<26}: {value:.2f}")
        else:
            print(f"  {name:<26}: {value:.2%}")


def build_signals(bars):
    """Every daily candle with each ETF's 3- and 12-month return worked out again from the
    raw closes, the quarterly checks, and the ETF each lookback picks at each check."""
    sessions = bars["NIFTYBEES"].index.union(bars["GOLDBEES"].index)
    frame = pd.DataFrame(index=sessions)
    for s in ETFS:
        close = bars[s]["close"]
        frame[f"{s}_close"] = close
        ema = pd.Series(ta.ema(close.to_numpy(), EMA_DAYS), index=close.index)
        frame[f"{s}_ema{EMA_DAYS}"] = ema.reindex(sessions).round(4)
        frame[f"{s}_above_ema"] = (close > ema).reindex(sessions)
        for months in (3, 12):
            n = lookback_sessions(months)
            # Each ETF's own candles, as the engine counts them (a day one ETF did not trade is skipped)
            frame[f"{s}_ret{months}m"] = ((close / close.shift(n) - 1) * 100).reindex(sessions).round(4)
    live = frame.index >= pd.Timestamp(START)
    quarter = frame.index.year * 10 + (frame.index.month - 1) // 3
    frame["check_day"] = live & (pd.Series(quarter, index=frame.index).diff() != 0).to_numpy()
    for months in (3, 12):
        rets = frame[[f"{s}_ret{months}m" for s in ETFS]].ffill()
        best = pd.Series(np.where(rets.iloc[:, 0] >= rets.iloc[:, 1], "NIFTYBEES", "GOLDBEES"), index=frame.index)
        frame[f"pick{months}m"] = best.where(frame["check_day"], "")
    frame.index.name = "date"
    return frame


def expected_trades(signals, bars, months, ema_filter="daily"):
    """Replay the rules day by day on the recomputed returns and EMAs. The quarterly check
    decides at the close of the quarter's first session and acts at the next session's
    open: it sells an ETF no longer picked there, and buys the pick there when nothing is
    held and the pick closed above its EMA on the check's candle. At every day's close:
    with the EMA exit ("daily"), a held ETF that closed below its EMA is sold at the next
    open; otherwise, when nothing is held, the pick is bought at the next open if it closed
    above its EMA ("daily", "entry") or at once ("off")."""
    dates = {s: bars[s].index for s in ETFS}
    sessions = signals.index[signals.index >= pd.Timestamp(START)]
    above = {s: signals[f"{s}_above_ema"].astype("boolean").ffill().fillna(False).astype(bool) for s in ETFS}

    def next_open(symbol, after):
        i = dates[symbol].searchsorted(after, side="right")
        return dates[symbol][i] if i < len(dates[symbol]) else pd.NaT

    def allows(symbol, day):
        return ema_filter == "off" or bool(above[symbol].at[day])

    timer = {}
    for day in signals.index[signals["check_day"]]:
        i = sessions.searchsorted(day, side="right")
        if i < len(sessions):
            timer[sessions[i]] = day
    rows, held, entry, want, pending, selling = [], None, None, None, None, None
    for day in sessions:
        if selling is not None and selling == day:                # yesterday's EMA exit fills at this open
            rows.append((held, entry, day))
            held, selling = None, None
        if pending is not None and pending[1] == day:             # yesterday's buy fills at this open
            held, entry, pending = pending[0], day, None
        if day in timer:                                          # the quarterly check acts at this open
            check = timer[day]
            want = signals.at[check, f"pick{months}m"]
            if held is not None and held != want:
                rows.append((held, entry, day))
                held = None
            elif held is None and pending is None and allows(want, check):
                held, entry = want, day
        # this day's close
        if held is not None and ema_filter == "daily" and not allows(held, day):
            selling = next_open(held, day)
        elif want is not None and held is None and pending is None and allows(want, day):
            pending = (want, next_open(want, day))
    if held is not None:
        rows.append((held, entry, pd.NaT))
    return pd.DataFrame(rows, columns=["symbol", "entry_date", "exit_date"])


def check_trades(r, expected):
    """The engine's trades (and the position still open) against the replay."""
    got = r.trade_list()[["symbol", "entry_time", "exit_time"]].copy()
    still = r.final_positions
    open_rows = []
    for s in still.loc[still["quantity_units"] != 0, "symbol"]:
        buys = r.fills[(r.fills["symbol"] == s) & (r.fills["side"] == "BUY")]
        open_rows.append({"symbol": s, "entry_time": buys["time"].max(), "exit_time": pd.NaT})
    if open_rows:
        got = pd.concat([got, pd.DataFrame(open_rows)], ignore_index=True)
    for col in ("entry_time", "exit_time"):
        got[col.replace("time", "date")] = (pd.to_datetime(got[col], utc=True).dt.tz_convert(IST)
                                            .dt.tz_localize(None).dt.normalize())
    got = got[["symbol", "entry_date", "exit_date"]]
    merged = expected.merge(got, on=["symbol", "entry_date"], how="outer",
                            suffixes=("_expected", "_engine"), indicator=True)
    merged["exit_matches"] = (merged["exit_date_expected"] == merged["exit_date_engine"]) | (
        merged["exit_date_expected"].isna() & merged["exit_date_engine"].isna())
    return merged.sort_values("entry_date")


def stray_opens(r, bars):
    """Fills at an opening price outside the closes around it (the day before and the day
    itself) by more than half a percent: what each one cost (+) or saved (-) in rupees."""
    rows = []
    for _, f in r.fills.iterrows():
        s = f["symbol"]
        day = pd.Timestamp(f["time"]).tz_convert(IST).tz_localize(None).normalize()
        closes = bars[s]["close"]
        i = closes.index.get_indexer([day])[0]
        if i <= 0:
            continue
        low, high = sorted((closes.iloc[i - 1], closes.iloc[i]))
        price, qty = f["price_rupees"], f["quantity_units"]
        if f["side"] == "BUY":
            off = price - high if price > high * 1.005 else price - low if price < low * 0.995 else 0.0
        else:
            off = low - price if price < low * 0.995 else high - price if price > high * 1.005 else 0.0
        if off:
            rows.append({"date": day.date(), "symbol": s, "side": f["side"], "fill_price": price,
                         "close_before": closes.iloc[i - 1], "close_that_day": closes.iloc[i],
                         "cost_rupees": round(off * qty, 2)})
    return pd.DataFrame(rows)


def cash_interest(r, sessions):
    """Rough rupees the account's cash days would have earned at the FD rate (whole account
    in cash only; the 5 percent buffer is left out)."""
    value = equity_of(r).reindex(sessions).ffill()
    held = holdings_by_day(r, sessions)
    gap_days = pd.Series(sessions[1:] - sessions[:-1], index=sessions[:-1]).dt.days
    daily_rate = (1 + FD_PCT / 100) ** (gap_days / 365) - 1
    in_cash = held.reindex(gap_days.index) == "cash"
    return float((value.reindex(gap_days.index) * daily_rate)[in_cash].sum())


def rolling_returns(curves, months):
    """Every `months`-month return of each account value, ending on each session."""
    table = {}
    for name, series in curves.items():
        start = series.index - pd.DateOffset(months=months)
        before = series.asof(start).to_numpy()
        values = pd.Series(series.to_numpy() / before - 1, index=series.index)
        table[name] = values[start >= series.index[0]]
    return pd.DataFrame(table)


def rolling_summary(curves):
    rows = []
    for months in (3, 12):
        fd = hurdle_over(months, FD_PCT) / 100
        frame = rolling_returns(curves, months)
        for name in frame:
            v = frame[name].dropna()
            rows.append({"window": f"{months} months", "portfolio": name, "average": v.mean(),
                         "median": v.median(), "worst": v.min(), "best": v.max(),
                         "share_positive": (v > 0).mean(), "share_above_fd": (v > fd).mean()})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- Plotly report
SURFACE, INK, INK_2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
FONT = "system-ui, -apple-system, Segoe UI, sans-serif"
SHADE = {"NIFTYBEES": "rgba(42,120,214,0.10)", "GOLDBEES": "rgba(235,104,52,0.12)"}


def layout(fig, title, subtitle, height, left=80):
    fig.update_layout(
        title=dict(text=f"{title}<br><span style='font-size:13px;color:{INK_2}'>{subtitle}</span>",
                   x=0, xanchor="left", font=dict(size=18, color=INK)),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, height=height,
        font=dict(family=FONT, size=12, color=INK_2), margin=dict(l=left, r=150, t=100, b=50),
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=AXIS, font=dict(family=FONT, color=INK)),
        legend=dict(orientation="h", x=0, y=1.02, yanchor="bottom", font=dict(color=INK_2)),
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont=dict(color=MUTED))
    return fig


def equity_chart(curves):
    fig = go.Figure()
    for name, (series, colour, dash) in curves.items():
        fig.add_trace(go.Scatter(x=series.index, y=series.values, name=name, mode="lines",
                                 line=dict(color=colour, width=2, dash=dash),
                                 hovertemplate=name + ": Rs %{y:,.0f}<extra></extra>"))
        fig.add_annotation(x=series.index[-1], y=series.values[-1], xanchor="left", xshift=6, showarrow=False,
                           text=f"{name}<br>Rs {series.values[-1] / 1e5:,.2f} lakh",
                           font=dict(color=INK_2, size=11), align="left")
    fig.add_hline(y=CAPITAL, line=dict(color=AXIS, width=1))
    layout(fig, "Account value, Rs 10 lakh invested",
           f"{START} to {END}, after charges. The grey line is the starting Rs 10 lakh.", 480)
    fig.update_yaxes(title=dict(text="account value (Rs)", font=dict(color=MUTED)), tickformat=",.0f")
    return fig


def drawdown_chart(curves):
    fig = go.Figure()
    for name, (series, colour, dash) in curves.items():
        dd = series / series.cummax() - 1
        fig.add_trace(go.Scatter(x=dd.index, y=dd.values, name=name, mode="lines",
                                 line=dict(color=colour, width=2, dash=dash),
                                 hovertemplate=name + ": %{y:.1%}<extra></extra>"))
        fig.add_annotation(x=dd.idxmin(), y=dd.min(), text=f"{dd.min():.1%}", showarrow=True, ax=0, ay=24,
                           arrowcolor=MUTED, font=dict(color=INK_2, size=11))
    layout(fig, "Drawdown: the fall from each account's highest value",
           "The lowest point of each line is its worst fall (max drawdown).", 420)
    fig.update_yaxes(title=dict(text="below the peak", font=dict(color=MUTED)), tickformat=".0%")
    return fig


def momentum_chart(signals, months, held, label):
    """Each ETF's return over the lookback, the FD hurdle, and what the strategy held."""
    fig = go.Figure()
    view = signals[signals.index >= pd.Timestamp(START)]
    # Shade the stretches the strategy held each ETF.
    run_id = (held != held.shift()).cumsum()
    for _, part in held.groupby(run_id):
        what = part.iloc[0]
        if what in SHADE:
            fig.add_vrect(x0=part.index[0], x1=part.index[-1] + pd.Timedelta(days=1), fillcolor=SHADE[what],
                          line_width=0, layer="below")
    for s, colour in (("NIFTYBEES", BLUE), ("GOLDBEES", ORANGE)):
        col = f"{s}_ret{months}m"
        fig.add_trace(go.Scatter(x=view.index, y=view[col] / 100, name=f"{s}, last {months} months",
                                 mode="lines", line=dict(color=colour, width=1.6),
                                 hovertemplate=s + ": %{y:.1%}<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=AXIS, width=1))
    layout(fig, f"{label}: the {months}-month return of each ETF, and what the strategy held",
           "Shaded blue: holding NIFTYBEES. Shaded orange: holding GOLDBEES. Unshaded: cash, below the 200-day EMA. "
           "Each quarter's first session picks the higher line.", 460)
    fig.update_yaxes(title=dict(text=f"return over {months} months", font=dict(color=MUTED)), tickformat=".0%")
    return fig


def ema_chart(signals, symbol, colour, held):
    """An ETF's daily close and its 200-day EMA, shaded where the baseline held it."""
    view = signals[signals.index >= pd.Timestamp(START)]
    fig = go.Figure()
    mine = held == symbol
    run_id = (mine != mine.shift()).cumsum()
    for _, part in mine.groupby(run_id):
        if part.iloc[0]:
            fig.add_vrect(x0=part.index[0], x1=part.index[-1] + pd.Timedelta(days=1), fillcolor=SHADE[symbol],
                          line_width=0, layer="below")
    fig.add_trace(go.Scatter(x=view.index, y=view[f"{symbol}_close"], name=f"{symbol} close", mode="lines",
                             line=dict(color=colour, width=1.4), hovertemplate="close Rs %{y:,.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=view.index, y=view[f"{symbol}_ema{EMA_DAYS}"], name=f"{EMA_DAYS}-day EMA",
                             mode="lines", line=dict(color=INK_2, width=1.4, dash="dash"),
                             hovertemplate="EMA Rs %{y:,.2f}<extra></extra>"))
    layout(fig, f"{symbol} and its {EMA_DAYS}-day EMA",
           f"Shaded: the 12-month baseline held {symbol}. It buys only above the EMA and sells on a close below it.",
           400)
    fig.update_yaxes(title=dict(text="price (Rs)", font=dict(color=MUTED)), tickformat=",.0f")
    return fig


def rolling_chart(curves, months):
    frame = rolling_returns({n: s for n, (s, _, _) in curves.items()}, months)
    fig = go.Figure()
    for name, (_, colour, dash) in curves.items():
        fig.add_trace(go.Scatter(x=frame.index, y=frame[name], name=name, mode="lines",
                                 line=dict(color=colour, width=1.6, dash=dash),
                                 hovertemplate=name + ": %{y:.1%}<extra></extra>"))
    fig.add_hline(y=hurdle_over(months, FD_PCT) / 100, line=dict(color=INK_2, width=1, dash="dash"),
                  annotation_text="FD", annotation_position="right", annotation_font=dict(color=INK_2, size=11))
    layout(fig, f"Rolling {months}-month return of each account",
           f"Each point is the return over the {months} months that end on that day, after charges.", 420)
    fig.update_yaxes(title=dict(text=f"{months}-month return", font=dict(color=MUTED)), tickformat=".0%")
    return fig


def table_html(frame, formats):
    head = "".join(f"<th>{c}</th>" for c in [frame.index.name or ""] + list(frame.columns))
    body = []
    for name, row in frame.iterrows():
        cells = "".join(f"<td>{formats.get(c, '{}').format(row[c]) if pd.notna(row[c]) else ''}</td>"
                        for c in frame.columns)
        body.append(f"<tr><th>{name}</th>{cells}</tr>")
    return f"<div class='table'><table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"


def write_report(intro, tables, figures, path):
    style = (f"body{{background:{SURFACE};color:{INK};font-family:{FONT};max-width:1100px;margin:24px auto;"
             f"padding:0 16px}}.chart{{margin:24px 0 40px}}.table{{overflow-x:auto;margin:12px 0 28px}}"
             f"table{{border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}}"
             f"th,td{{padding:6px 10px;border-bottom:1px solid {GRID};text-align:right;white-space:nowrap}}"
             f"tbody th,thead th:first-child{{text-align:left}}h2{{font-size:18px;margin-top:32px}}"
             f"p{{max-width:70ch;line-height:1.5;color:{INK_2}}}")
    parts = [f"<html><head><meta charset='utf-8'><title>Strategy 06 report</title><style>{style}</style>"
             f"</head><body><h1 style='font-size:24px'>Strategy 06: dual momentum on NIFTYBEES and GOLDBEES, "
             f"checked every quarter</h1>{intro}"]
    for heading, html in tables:
        parts.append(f"<h2>{heading}</h2>{html}")
    for i, fig in enumerate(figures):
        parts.append("<div class='chart'>" + fig.to_html(full_html=False, include_plotlyjs=(i == 0),
                                                       config={"displaylogo": False}) + "</div>")
    parts.append("</body></html>")
    path.write_text("".join(parts), encoding="utf-8")


# ---------------------------------------------------------------- the run
if __name__ == "__main__":
    REPORTS.mkdir(exist_ok=True)
    # Every run reads Historify (source="db"), fills at the next open, and is charged.
    RUN = dict(start=START, end=END, capital=CAPITAL, source="db", benchmark="NIFTY",
               costs=bt.costs.CostModel(backfill=True))

    bars = {s: historify(s) for s in ETFS}
    sessions = bars["NIFTYBEES"].index.union(bars["GOLDBEES"].index)
    sessions = sessions[sessions >= pd.Timestamp(START)]
    for s in ETFS:
        missing = sessions.difference(bars[s].index)
        if len(missing):
            print(f"Note: Historify has no {s} candle on {', '.join(str(d.date()) for d in missing)}")

    # 1. The baseline (12-month lookback) and the 3-month lookback asked for: the stronger
    #    ETF each quarter, bought only above its 200-day EMA, no crash filter
    base = bt.backtest(Momentum, client, **RUN)
    three = bt.backtest(Momentum, client, **RUN, params={"lookback_months": 3})
    print(base.summary())
    for label, r in (("Stronger ETF + EMA filter, 12-month lookback (baseline)", base),
                     ("Stronger ETF + EMA filter, 3-month lookback", three)):
        show(label, headline(r, sessions))
        m = r.metrics
        print(f"  NIFTY over the test         : {m['benchmark_total_return']:.2%}   beta {m['beta']:.2f}")
        print("  Year by year                :",
              ", ".join(f"{y} {v:.2%}" for y, v in r.performance.yearly_returns.items()))
        t = r.trade_list()
        print(t[["symbol", "entry_time", "exit_time", "entry_price", "exit_price", "net_pnl", "return_pct",
                 "days_held"]].to_string())
        interest = cash_interest(r, sessions)
        print(f"  FD interest the cash days would have earned (estimate): Rs {interest:,.0f}")

    # 2. Variants: the EMA filter taken apart, settings looked at (not tuned), and the
    #    removed crash filter for comparison
    variants = {
        "Stronger ETF, 12-month, no EMA filter": dict(ema_filter="off"),
        "Stronger ETF, 3-month, no EMA filter": dict(lookback_months=3, ema_filter="off"),
        "EMA for entries only, 12-month": dict(ema_filter="entry"),
        "EMA for entries only, 3-month": dict(lookback_months=3, ema_filter="entry"),
        "Stronger ETF + EMA filter, 6-month": dict(lookback_months=6),
        "Stronger ETF + EMA filter, 9-month": dict(lookback_months=9),
        "Stronger ETF + EMA filter, 12-month, checked monthly": dict(check_every="month"),
        "Stronger ETF + EMA filter, 3-month, checked monthly": dict(lookback_months=3, check_every="month"),
        "Crash filter (6% FD), no EMA, 12-month": dict(mode="dual", ema_filter="off"),
        "Crash filter (6% FD), no EMA, 3-month": dict(mode="dual", lookback_months=3, ema_filter="off"),
        "Crash filter at 0%, no EMA, 3-month": dict(mode="dual", lookback_months=3, hurdle_pct=0.0, ema_filter="off"),
        "Crash filter only, 12-month": dict(mode="absolute", ema_filter="off"),
        "Crash filter only, 3-month": dict(mode="absolute", lookback_months=3, ema_filter="off"),
    }
    variant_runs = {name: bt.backtest(Momentum, client, **RUN, params=p) for name, p in variants.items()}

    # 3. Yardsticks: the same two ETFs held
    holds = {
        "NIFTYBEES held": bt.backtest(HoldMix, client, **RUN, params={"nifty_pct": 100}),
        "GOLDBEES held": bt.backtest(HoldMix, client, **RUN, params={"nifty_pct": 0}),
        "60:40 held (strategy 03 mix)": bt.backtest(HoldMix, client, **RUN, params={"nifty_pct": 60}),
        "50:50 reset every quarter": bt.backtest(HoldMix, client, **RUN,
                                                 params={"nifty_pct": 50, "reset_every": "quarter"}),
    }
    runs = {"Stronger ETF + EMA filter, 12-month (baseline)": base, "Stronger ETF + EMA filter, 3-month": three,
            **variant_runs, **holds}
    rows = {}
    for name, r in runs.items():
        m, t = r.metrics, r.trade_list()
        held = holdings_by_day(r, sessions)
        rows[name] = {"net_profit": m["net_profit"], "cagr": m["cagr"], "max_drawdown": m["max_drawdown"],
                      "volatility": m["volatility"], "sharpe": m["sharpe"], "closed_trades": len(t),
                      "days_in_cash": (held == "cash").mean(), "charges": r.costs["charged"].sum()}
    # The NIFTY 50 index itself (a price index: no dividends, no charges, not tradable as such)
    nifty = historify("NIFTY", start=START, exchange="NSE_INDEX")["close"]
    years = (nifty.index[-1] - nifty.index[0]).days / 365.25
    rows["NIFTY 50 index (benchmark)"] = {
        "net_profit": float("nan"), "cagr": (nifty.iloc[-1] / nifty.iloc[0]) ** (1 / years) - 1,
        "max_drawdown": (nifty / nifty.cummax() - 1).min(), "volatility": nifty.pct_change().std() * math.sqrt(SESSIONS_PER_YEAR),
        "sharpe": float("nan"), "closed_trades": float("nan"), "days_in_cash": float("nan"), "charges": float("nan")}
    compared = pd.DataFrame(rows).T
    compared.index.name = "portfolio"
    print(f"\n== Compared ({START} to {END}; NIFTY 50 index: {base.metrics['benchmark_total_return']:.2%})")
    fmt = {"net_profit": "{:,.0f}".format, "cagr": "{:.2%}".format, "max_drawdown": "{:.2%}".format,
           "volatility": "{:.2%}".format, "sharpe": "{:.2f}".format, "closed_trades": "{:.0f}".format,
           "days_in_cash": "{:.1%}".format, "charges": "{:,.0f}".format}
    print(compared.to_string(formatters=fmt))

    # 4. Rolling 3- and 12-month returns, the strategy against holding the ETFs
    curves = {"With EMA filter, 12-month": equity_of(base), "With EMA filter, 3-month": equity_of(three),
              "No EMA filter, 12-month": equity_of(variant_runs["Stronger ETF, 12-month, no EMA filter"]),
              "No EMA filter, 3-month": equity_of(variant_runs["Stronger ETF, 3-month, no EMA filter"]),
              "NIFTYBEES held": equity_of(holds["NIFTYBEES held"]),
              "GOLDBEES held": equity_of(holds["GOLDBEES held"]),
              "60:40 held": equity_of(holds["60:40 held (strategy 03 mix)"])}
    rolling = rolling_summary(curves)
    print("\n== Rolling returns: every 3- and 12-month stretch of the test")
    print(rolling.to_string(index=False, formatters={c: "{:.1%}".format for c in rolling.columns[2:]}))

    # 5. Reality checks: worse fills and late orders
    print("\n== Reality checks (net profit, and the share of the backtest's kept)")
    for label, r, params in (("12-month", base, {}), ("3-month", three, {"lookback_months": 3})):
        for how, kwargs in (("filled at the next close", {"fill": "next_close"}),
                            ("every order one day late", {"delay_entries": 1, "delay_exits": 1})):
            check = bt.backtest(Momentum, client, **RUN, params=params, **kwargs)
            profit = check.metrics["net_profit"]
            kept = f"{profit / r.metrics['net_profit']:.0%} kept" if r.metrics["net_profit"] > 0 else "baseline lost"
            print(f"  {label}, {how:<26}: Rs {profit:,.0f} ({kept})")

    # 6. Warnings and rejected orders
    print("\n== Warnings (baseline)")
    for line in base.warnings:
        print("  -", line)
    for label, r in (("12-month", base), ("3-month", three)):
        refused = r.orders[r.orders["status"] == "Rejected"]
        print(f"  Rejected orders, {label}: {len(refused)}",
              refused[["symbol", "decided_at", "reject_code"]].to_dict("records") if len(refused) else "")

    # 7. Cross-check: the trades against the rules replayed on recomputed returns
    signals = build_signals(bars)
    checks = {}
    print("\n== Cross-check against the returns worked out again from Historify's closes")
    for label, r, months in (("12-month", base, 12), ("3-month", three, 3)):
        checked = check_trades(r, expected_trades(signals, bars, months))
        checks[label] = checked
        both = checked["_merge"] == "both"
        print(f"  {label}: {both.sum()} of {len(checked)} trades match on entry day, "
              f"{checked.loc[both, 'exit_matches'].sum()} also on exit day; "
              f"only in the replay {(checked['_merge'] == 'left_only').sum()}, "
              f"only in the engine {(checked['_merge'] == 'right_only').sum()}")
        odd = checked[~(both & checked["exit_matches"])]
        if len(odd):
            print(odd.to_string(index=False))

    # 8. Stray opening prices on the fills
    print("\n== Fills at a stray opening price (more than 0.5% outside the closes around them)")
    strays = {label: stray_opens(r, bars) for label, r in (("12-month", base), ("3-month", three))}
    for label, frame in strays.items():
        cost = frame["cost_rupees"].sum() if len(frame) else 0.0
        print(f"  {label}: {len(frame)} fills, net cost Rs {cost:,.0f} (+ = paid more than the closes around it)")
        if len(frame):
            print(frame.to_string(index=False))

    # 9. Files
    signals_out = signals[signals.index >= pd.Timestamp(START)].copy()
    signals_out["held12m"] = holdings_by_day(base, signals_out.index)
    signals_out["held3m"] = holdings_by_day(three, signals_out.index)
    signals_out.to_csv(REPORTS / "signals.csv")
    columns = ["symbol", "entry_time", "exit_time", "quantity", "entry_price", "exit_price", "gross_pnl",
               "charges", "net_pnl", "return_pct", "bars_held", "days_held", "mae", "mfe", "exit_reason"]
    base.trade_list()[columns].to_csv(REPORTS / "trades.csv")
    three.trade_list()[columns].to_csv(REPORTS / "trades_3m.csv")
    base.final_positions.to_csv(REPORTS / "open_positions.csv", index=False)
    compared.to_csv(REPORTS / "compared.csv")
    rolling.to_csv(REPORTS / "rolling_returns.csv", index=False)
    pd.concat({k: v.drop(columns="_merge").assign(found_in=v["_merge"].astype(str)) for k, v in checks.items()},
              names=["lookback"]).to_csv(REPORTS / "trade_check.csv")
    pd.concat(strays, names=["lookback"]).to_csv(REPORTS / "stray_opens.csv")
    base.to_csv(str(REPORTS / "tables"))
    base.tearsheet(str(REPORTS / "tearsheet.html"))
    three.tearsheet(str(REPORTS / "tearsheet_3m.html"))

    chart_curves = {"With EMA filter, 12-month": (curves["With EMA filter, 12-month"], BLUE, "solid"),
                    "With EMA filter, 3-month": (curves["With EMA filter, 3-month"], ORANGE, "solid"),
                    "No EMA filter, 12-month": (curves["No EMA filter, 12-month"], AQUA, "solid"),
                    "50:50 reset quarterly": (equity_of(holds["50:50 reset every quarter"]), MUTED, "dot")}
    intro = ("<p>Once a quarter the strategy picks whichever ETF rose more over the lookback (Antonacci's dual "
             "momentum with its crash filter removed) and holds it only while its daily close is above its "
             f"200-day EMA. {START} to {END}, Rs 10 lakh, charges and slippage included, orders filled at the "
             "next open. Data: Historify daily candles.</p>")
    show_cols = compared.rename(columns={"net_profit": "net profit (Rs)", "max_drawdown": "worst fall",
                                         "closed_trades": "closed trades", "days_in_cash": "days in cash",
                                         "charges": "charges (Rs)"})
    roll_view = rolling.set_index(rolling["window"] + ", " + rolling["portfolio"]).drop(columns=["window", "portfolio"])
    roll_view.index.name = "window, portfolio"
    write_report(intro, [
        ("Every run compared", table_html(show_cols, {
            "net profit (Rs)": "{:,.0f}", "cagr": "{:.2%}", "worst fall": "{:.2%}", "volatility": "{:.2%}",
            "sharpe": "{:.2f}", "closed trades": "{:.0f}", "days in cash": "{:.1%}", "charges (Rs)": "{:,.0f}"})),
        ("Rolling 3- and 12-month returns", table_html(roll_view, {c: "{:.1%}" for c in roll_view.columns})),
    ], [
        equity_chart(chart_curves),
        drawdown_chart(chart_curves),
        momentum_chart(signals, 12, signals_out["held12m"], "12-month lookback"),
        momentum_chart(signals, 3, signals_out["held3m"], "3-month lookback"),
        ema_chart(signals, "NIFTYBEES", BLUE, signals_out["held12m"]),
        ema_chart(signals, "GOLDBEES", ORANGE, signals_out["held12m"]),
        rolling_chart(chart_curves, 12),
        rolling_chart(chart_curves, 3),
    ], REPORTS / "strategy_report.html")
    print(f"\nSaved in {REPORTS}: strategy_report.html, tearsheet.html, tearsheet_3m.html, trades.csv, "
          "trades_3m.csv, open_positions.csv, signals.csv, compared.csv, rolling_returns.csv, "
          "trade_check.csv, stray_opens.csv, tables/")
