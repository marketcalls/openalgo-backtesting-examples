"""
Strategy 04: custom tearsheet with each stock's own equity curve and drawdown

Reads the tables that strategy.py saved in reports/tables (fills, charges, account value)
and each stock's prices from Historify, and writes reports/custom_tearsheet.html (Plotly).
It does not run the backtest again: run strategy.py first.

How a stock's curve is worked out
  Every fill of the stock is a cash flow: a buy pays (units x price) plus its charges, a sale
  receives (units x price) less its charges. At the end of each trading day the stock's
  profit so far is all its cash flows to date plus the shares still held at that day's last
  price. The ten stock curves therefore add up to the account's own profit; the script
  checks this against the engine's account value and prints the largest gap.
Stock equity and drawdown
  Equal allocation puts about a tenth of the money in each stock, so each stock is shown as
  a Rs 1,00,000 sleeve: Rs 1,00,000 plus that stock's profit so far. Its drawdown is the fall
  from the sleeve's highest value. The grey line beside it is Rs 1,00,000 put into the stock
  on the day of the strategy's first order and simply held (no charges).

Run       : python tearsheet.py   (from this folder; needs pandas, plotly, the OpenAlgo
            server running and OPENALGO_API_KEY in the .env file of "backtesting examples")
"""
import html
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openalgo import api

HERE = Path(__file__).resolve().parent
REPORTS = HERE / "reports"
TABLES = REPORTS / "tables"

START = "2021-11-22"
END = "2026-11-20"
CAPITAL = 10_00_000
SLEEVE = 1_00_000  # each stock's notional share of the Rs 10 lakh
BASKET = ("MAXHEALTH", "ONGC", "HINDUNILVR", "ETERNAL", "CIPLA",
          "INFY", "POWERGRID", "BAJAJ-AUTO", "KOTAKBANK", "ADANIENT")
SESSIONS_PER_YEAR = 248

# Colours (validated categorical slot 1, grey for the yardstick, a blue to grey to red scale for gains and losses)
SURFACE, INK, INK_2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, HOLD_GREY, RED = "#2a78d6", "#a9a79f", "#e34948"
GAIN_LOSS = [[0.0, "#a8302f"], [0.25, "#e97f7e"], [0.5, "#f0efec"], [0.75, "#5598e7"], [1.0, "#184f95"]]
FONT = "system-ui, -apple-system, Segoe UI, sans-serif"


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


load_env()
client = api(api_key=os.environ["OPENALGO_API_KEY"],
             host=os.environ.get("OPENALGO_HOST", "http://127.0.0.1:5000"))


# ---------------------------------------------------------------- numbers

def inr(x, decimals=0):
    """Indian digit grouping: 12,34,567."""
    sign = "-" if x < 0 else ""
    whole, _, frac = f"{abs(x):.{decimals}f}".partition(".")
    head, tail = whole[:-3], whole[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    text = ",".join(groups + [tail]) if groups else tail
    return f"{sign}Rs {text}" + (f".{frac}" if decimals else "")


def day_end_marks():
    """Each stock's last traded price of every day, from Historify's hourly candles."""
    marks = {}
    for s in BASKET:
        bars = client.history(symbol=s, exchange="NSE", interval="1h", start_date=START, end_date=END, source="db")
        if not hasattr(bars, "index"):
            raise SystemExit(f"Historify returned no hourly candles for {s}: {bars}")
        close = bars["close"]
        close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
        marks[s] = close.groupby(level=0).last()
    return pd.DataFrame(marks).sort_index().ffill()


def stock_pnl(fills, marks):
    """Each stock's profit so far at every day's end: cash flows to date plus shares held at the mark."""
    f = fills.copy()
    f["date"] = pd.to_datetime(f["time"]).dt.normalize()
    f["units"] = np.where(f["side"] == "BUY", f["quantity_units"], -f["quantity_units"])
    f["cash"] = -f["units"] * f["price_rupees"] - f["costs_rupees"]
    days = marks.index
    cash = f.pivot_table(index="date", columns="symbol", values="cash", aggfunc="sum").reindex(days).fillna(0).cumsum()
    units = f.pivot_table(index="date", columns="symbol", values="units", aggfunc="sum").reindex(days).fillna(0).cumsum()
    cash, units = cash.reindex(columns=BASKET).fillna(0), units.reindex(columns=BASKET).fillna(0)
    return cash + units * marks[list(BASKET)], units


def account_day_end():
    """The engine's account value at the end of each day (its table has a row per minute)."""
    eq = pd.read_csv(TABLES / "equity.csv", usecols=["time", "equity_rupees"], parse_dates=["time"])
    eq["date"] = eq["time"].dt.normalize()
    return eq.groupby("date")["equity_rupees"].last()


def drawdown(series):
    return series / series.cummax() - 1


def longest_drawdown_days(series):
    """The most calendar days spent below a previous high."""
    peak_day, longest = series.index[0], 0
    running_max = -np.inf
    for day, value in series.items():
        if value >= running_max:
            running_max, peak_day = value, day
        else:
            longest = max(longest, (day - peak_day).days)
    return longest


def stock_stats(pnl, units, trades, marks, first_day):
    rows = []
    for s in BASKET:
        t = trades[trades["symbol"] == s]
        sleeve = SLEEVE + pnl[s]
        dd = drawdown(sleeve)
        wins, losses = t.loc[t["net_pnl_rupees"] > 0, "net_pnl_rupees"], t.loc[t["net_pnl_rupees"] <= 0, "net_pnl_rupees"]
        held = marks.loc[first_day:, s]
        rows.append({
            "Stock": s,
            "Profit": pnl[s].iloc[-1],
            "Sleeve return": pnl[s].iloc[-1] / SLEEVE,
            "Holding the stock": held.iloc[-1] / held.iloc[0] - 1,
            "Max drawdown": dd.min(),
            "Max drawdown (Rs)": (sleeve - sleeve.cummax()).min(),
            "Longest drawdown (days)": longest_drawdown_days(sleeve),
            "Closed trades": len(t),
            "Win rate": (t["net_pnl_rupees"] > 0).mean() if len(t) else np.nan,
            "Profit factor": wins.sum() / -losses.sum() if losses.sum() < 0 else np.nan,
            "Best trade": t["net_pnl_rupees"].max(),
            "Worst trade": t["net_pnl_rupees"].min(),
            "Days held": (units.loc[first_day:, s] > 0).mean(),
            "Charges": t["costs_rupees"].sum(),
        })
    return pd.DataFrame(rows).set_index("Stock").sort_values("Profit", ascending=False)


def portfolio_stats(equity, trades, fills, first_day):
    rets = equity.pct_change().dropna()
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    dd = drawdown(equity)
    return {
        "Net profit": inr(equity.iloc[-1] - CAPITAL, 2),
        "CAGR": f"{(equity.iloc[-1] / CAPITAL) ** (1 / years) - 1:.2%}",
        "Max drawdown": f"{dd.min():.2%}",
        "Volatility (yearly)": f"{rets.std() * np.sqrt(SESSIONS_PER_YEAR):.2%}",
        "Sharpe ratio": f"{rets.mean() / rets.std() * np.sqrt(SESSIONS_PER_YEAR):.2f}",
        "Closed trades": f"{len(trades):,}",
        "Win rate": f"{(trades['net_pnl_rupees'] > 0).mean():.1%}",
        "Charges": inr(fills["costs_rupees"].sum()),
        "First order": f"{first_day:%d %b %Y}",
    }


# ---------------------------------------------------------------- charts

def style(fig, height, left=70):
    fig.update_layout(
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, height=height, font=dict(family=FONT, size=12, color=INK_2),
        margin=dict(l=left, r=30, t=40, b=40), showlegend=False,
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=AXIS, font=dict(family=FONT, color=INK)),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont=dict(color=MUTED))
    fig.update_annotations(font=dict(color=INK, size=13))
    return fig


def portfolio_chart(equity):
    """Account value and its drawdown, one above the other, each on its own axis."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.62, 0.38],
                        subplot_titles=("Account value (Rs lakh)", "Drawdown: fall from the highest value"))
    fig.add_trace(go.Scatter(x=equity.index, y=equity / 1e5, mode="lines", line=dict(color=BLUE, width=2),
                             hovertemplate="%{x|%d %b %Y}<br>Rs %{y:.2f} lakh<extra></extra>"), row=1, col=1)
    fig.add_hline(y=CAPITAL / 1e5, line=dict(color=AXIS, width=1), row=1, col=1)
    dd = drawdown(equity)
    fig.add_trace(go.Scatter(x=dd.index, y=dd, mode="lines", line=dict(color=RED, width=1.5), fill="tozeroy",
                             fillcolor="rgba(227,73,72,0.10)", hovertemplate="%{x|%d %b %Y}<br>%{y:.1%}<extra></extra>"),
                  row=2, col=1)
    fig.add_annotation(x=dd.idxmin(), y=dd.min(), text=f"worst {dd.min():.1%}", showarrow=True, ax=0, ay=26,
                       arrowcolor=MUTED, font=dict(color=INK_2), row=2, col=1)
    style(fig, 560)
    fig.update_yaxes(tickformat=".0%", row=2, col=1)
    fig.update_layout(hovermode="x unified")
    return fig


def profit_bars(stats):
    t = stats.sort_values("Profit")
    fig = go.Figure(go.Bar(
        x=t["Profit"], y=t.index, orientation="h", marker=dict(color=[BLUE if v >= 0 else RED for v in t["Profit"]]),
        text=[inr(v) for v in t["Profit"]], textposition="outside", cliponaxis=False, textfont=dict(color=INK_2),
        customdata=np.column_stack([t["Closed trades"], t["Holding the stock"]]),
        hovertemplate="%{y}<br>profit Rs %{x:,.0f}<br>%{customdata[0]} closed trades<br>the stock held: %{customdata[1]:.1%}<extra></extra>",
    ))
    style(fig, 420, left=100)
    fig.update_layout(barcornerradius=4, bargap=0.35, margin=dict(l=100, r=90, t=20, b=40))
    fig.update_xaxes(title=dict(text="profit after charges (Rs)", font=dict(color=MUTED)), tickformat=",.0f")
    fig.update_yaxes(showgrid=False, tickfont=dict(color=INK_2))
    return fig


def small_multiples(stats, pnl, marks, first_day, kind):
    """One panel per stock, in order of profit. kind = "equity" or "drawdown"."""
    order = list(stats.index)
    deepest = min(min(drawdown((SLEEVE + pnl[s]).loc[first_day:]).min(),
                      drawdown(marks.loc[first_day:, s]).min()) for s in order)
    titles = []
    for s in order:
        if kind == "equity":
            titles.append(f"{s}: {inr(stats.loc[s, 'Profit'])} ({stats.loc[s, 'Sleeve return']:+.1%})")
        else:
            titles.append(f"{s}: worst {stats.loc[s, 'Max drawdown']:.1%}")
    fig = make_subplots(rows=5, cols=2, shared_xaxes=True, vertical_spacing=0.06, horizontal_spacing=0.08,
                        subplot_titles=titles)
    for i, s in enumerate(order):
        r, c = i // 2 + 1, i % 2 + 1
        sleeve = (SLEEVE + pnl[s]).loc[first_day:]
        held = marks.loc[first_day:, s] / marks.loc[first_day, s] * SLEEVE
        if kind == "equity":
            fig.add_trace(go.Scatter(x=held.index, y=held / 1e3, mode="lines", line=dict(color=HOLD_GREY, width=1.5),
                                     name="Rs 1 lakh held in the stock", legendgroup="hold", showlegend=(i == 0),
                                     hovertemplate=s + " held<br>%{x|%d %b %Y}: Rs %{y:,.1f}k<extra></extra>"), row=r, col=c)
            fig.add_trace(go.Scatter(x=sleeve.index, y=sleeve / 1e3, mode="lines", line=dict(color=BLUE, width=2),
                                     name="Strategy on the stock (Rs 1 lakh sleeve)", legendgroup="strategy",
                                     showlegend=(i == 0),
                                     hovertemplate=s + " strategy<br>%{x|%d %b %Y}: Rs %{y:,.1f}k<extra></extra>"), row=r, col=c)
            fig.add_hline(y=SLEEVE / 1e3, line=dict(color=AXIS, width=1), row=r, col=c)
        else:
            held_dd, dd = drawdown(held), drawdown(sleeve)
            fig.add_trace(go.Scatter(x=held_dd.index, y=held_dd, mode="lines", line=dict(color=HOLD_GREY, width=1.5),
                                     name="Rs 1 lakh held in the stock", legendgroup="hold", showlegend=(i == 0),
                                     hovertemplate=s + " held<br>%{x|%d %b %Y}: %{y:.1%}<extra></extra>"), row=r, col=c)
            fig.add_trace(go.Scatter(x=dd.index, y=dd, mode="lines", line=dict(color=BLUE, width=2),
                                     fill="tozeroy", fillcolor="rgba(42,120,214,0.10)",
                                     name="Strategy on the stock", legendgroup="strategy", showlegend=(i == 0),
                                     hovertemplate=s + " strategy<br>%{x|%d %b %Y}: %{y:.1%}<extra></extra>"), row=r, col=c)
    style(fig, 1250)
    fig.update_layout(showlegend=True, legend=dict(orientation="h", x=0, y=1.04, yanchor="bottom", font=dict(color=INK_2)),
                      margin=dict(l=60, r=30, t=90, b=40))
    if kind == "equity":
        fig.update_yaxes(ticksuffix="k")
    else:
        fig.update_yaxes(tickformat=".0%", range=[deepest * 1.05, 0.02])  # one scale for all ten panels
    return fig


def year_heatmap(pnl):
    """Each stock's profit in each calendar year (rupees): blue made money, red lost."""
    year_end = pnl.groupby(pnl.index.year).last()
    by_year = year_end.diff()
    by_year.iloc[0] = year_end.iloc[0]
    by_year = by_year.T.loc[list(pnl.iloc[-1].sort_values(ascending=False).index)]
    by_year.loc["All 10 stocks"] = by_year.sum()
    limit = float(np.nanmax(np.abs(by_year.values)))
    text = [[inr(v) for v in row] for row in by_year.values]
    fig = go.Figure(go.Heatmap(
        z=by_year.values, x=[str(y) for y in by_year.columns], y=list(by_year.index), zmin=-limit, zmax=limit, zmid=0,
        colorscale=GAIN_LOSS, text=text, texttemplate="%{text}", textfont=dict(size=11, color=INK), xgap=2, ygap=2,
        hovertemplate="%{y}, %{x}<br>%{text}<extra></extra>",
        colorbar=dict(title=dict(text="profit (Rs)", font=dict(color=INK_2)), tickfont=dict(color=MUTED),
                      outlinewidth=0, thickness=10, tickformat=",.0f"),
    ))
    style(fig, 470, left=110)
    fig.update_xaxes(showgrid=False, side="top", tickfont=dict(color=INK_2))
    fig.update_yaxes(showgrid=False, autorange="reversed", tickfont=dict(color=INK_2))
    return fig


def monthly_heatmap(equity):
    """The account's return in each month."""
    month_end = equity.resample("ME").last()
    rets = month_end.pct_change()
    rets.iloc[0] = month_end.iloc[0] / CAPITAL - 1
    grid = pd.DataFrame({"year": rets.index.year, "month": rets.index.month, "r": rets.values}).pivot(
        index="year", columns="month", values="r").reindex(columns=range(1, 13))
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    limit = float(np.nanmax(np.abs(grid.values)))
    text = [["" if pd.isna(v) else f"{v:.1%}" for v in row] for row in grid.values]
    fig = go.Figure(go.Heatmap(
        z=grid.values, x=months, y=[str(y) for y in grid.index], zmin=-limit, zmax=limit, zmid=0, colorscale=GAIN_LOSS,
        text=text, texttemplate="%{text}", textfont=dict(size=11, color=INK), xgap=2, ygap=2,
        hovertemplate="%{x} %{y}<br>%{text}<extra></extra>",
        colorbar=dict(title=dict(text="return", font=dict(color=INK_2)), tickfont=dict(color=MUTED),
                      outlinewidth=0, thickness=10, tickformat=".0%"),
    ))
    style(fig, 330, left=60)
    fig.update_xaxes(showgrid=False, side="top", tickfont=dict(color=INK_2))
    fig.update_yaxes(showgrid=False, autorange="reversed", tickfont=dict(color=INK_2))
    return fig


# ---------------------------------------------------------------- page

def stats_table(stats):
    head = ["Stock", "Profit", "Sleeve return", "Holding the stock", "Max drawdown", "Max drawdown (Rs)",
            "Longest drawdown", "Closed trades", "Win rate", "Profit factor", "Best trade", "Worst trade",
            "Days held", "Charges"]
    rows = []
    for s, r in stats.iterrows():
        cells = [s, inr(r["Profit"]), f"{r['Sleeve return']:+.1%}", f"{r['Holding the stock']:+.1%}",
                 f"{r['Max drawdown']:.1%}", inr(r["Max drawdown (Rs)"]), f"{r['Longest drawdown (days)']:,} days",
                 f"{r['Closed trades']}", f"{r['Win rate']:.0%}", f"{r['Profit factor']:.2f}", inr(r["Best trade"]),
                 inr(r["Worst trade"]), f"{r['Days held']:.0%}", inr(r["Charges"])]
        rows.append("<tr>" + "".join(f"<td{' class=n' if i else ''}>{html.escape(c)}</td>" for i, c in enumerate(cells)) + "</tr>")
    return ("<div class='scroll'><table><thead><tr>" + "".join(f"<th{' class=n' if i else ''}>{h}</th>"
            for i, h in enumerate(head)) + "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def section(title, note, body):
    return f"<section><h2>{title}</h2><p class='note'>{note}</p>{body}</section>"


def write_page(path, kpis, blocks):
    css = f"""
    body {{ background:{SURFACE}; color:{INK}; font-family:{FONT}; margin:0; }}
    .wrap {{ max-width:1120px; margin:0 auto; padding:28px 16px 64px; }}
    h1 {{ font-size:26px; margin:0 0 6px; }} h2 {{ font-size:19px; margin:0 0 4px; }}
    .sub {{ color:{INK_2}; margin:0 0 20px; max-width:80ch; line-height:1.5; }}
    .kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:14px; margin:8px 0 36px; }}
    .kpi {{ border-top:2px solid {INK}; padding-top:8px; }} .kpi .l {{ font-size:12px; color:{INK_2}; }}
    .kpi .v {{ font-size:22px; font-weight:600; margin-top:4px; font-variant-numeric:tabular-nums; }}
    section {{ margin:36px 0; }} .note {{ color:{INK_2}; margin:0 0 10px; max-width:85ch; line-height:1.5; font-size:14px; }}
    .scroll {{ overflow-x:auto; }} table {{ border-collapse:collapse; font-size:13px; width:100%; }}
    th, td {{ padding:7px 10px; border-bottom:1px solid {GRID}; white-space:nowrap; text-align:left; }}
    th {{ color:{INK_2}; font-weight:500; font-size:12px; }} .n {{ text-align:right; font-variant-numeric:tabular-nums; }}
    .method {{ font-size:13px; color:{INK_2}; line-height:1.55; max-width:90ch; }}
    """
    tiles = "".join(f"<div class='kpi'><div class='l'>{k}</div><div class='v'>{html.escape(v)}</div></div>"
                    for k, v in kpis.items())
    page = (f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>Strategy 04 tearsheet</title><style>{css}</style></head><body><div class='wrap'>"
            f"<h1>Strategy 04 tearsheet: Supertrend on the 10 least correlated NIFTY 50 stocks</h1>"
            f"<p class='sub'>Supertrend (10, 3) on hourly candles, long only, each stock bought with 9.5 percent of the "
            f"account. Rs 10 lakh, {START} to {END}, data from Historify. Hover over any chart for exact values.</p>"
            f"<div class='kpis'>{tiles}</div>{''.join(blocks)}</div></body></html>")
    path.write_text(page, encoding="utf-8")


if __name__ == "__main__":
    fills = pd.read_csv(TABLES / "fills.csv")
    trades = pd.read_csv(TABLES / "trades.csv")
    marks = day_end_marks()
    pnl, units = stock_pnl(fills, marks)
    first_day = pd.to_datetime(fills["time"]).min().normalize()

    # Check: the ten stock curves must add up to the engine's own account value
    account = account_day_end()
    ours = (CAPITAL + pnl.sum(axis=1)).reindex(account.index).ffill()
    gap = (ours - account).abs()
    print(f"Ten stock curves against the engine's account value: largest daily gap Rs {gap.max():,.2f}, "
          f"last day Rs {gap.iloc[-1]:,.2f} (account Rs {account.iloc[-1]:,.2f})")

    stats = stock_stats(pnl, units, trades, marks, first_day)
    print(stats[["Profit", "Sleeve return", "Holding the stock", "Max drawdown", "Closed trades", "Win rate"]]
          .to_string(formatters={"Profit": "{:,.0f}".format, "Sleeve return": "{:+.1%}".format,
                                 "Holding the stock": "{:+.1%}".format, "Max drawdown": "{:.1%}".format,
                                 "Win rate": "{:.0%}".format}))

    figs = {
        "portfolio": portfolio_chart(account),
        "profit": profit_bars(stats),
        "equity": small_multiples(stats, pnl, marks, first_day, "equity"),
        "drawdown": small_multiples(stats, pnl, marks, first_day, "drawdown"),
        "years": year_heatmap(pnl),
        "months": monthly_heatmap(account),
    }
    first = [True]

    def plot(name):
        out = figs[name].to_html(full_html=False, include_plotlyjs=first[0], config={"displaylogo": False})
        first[0] = False
        return out

    method = (f"<p>Each stock's curve is built from its own fills: a buy pays units x price plus charges, a sale "
              f"receives units x price less charges, and shares still held are valued at each day's last traded price "
              f"(from Historify's hourly candles). The ten curves add up to the account: the largest daily gap "
              f"against the engine's own account value is {inr(gap.max(), 2)}. Each stock is shown as a Rs 1,00,000 "
              f"sleeve (its tenth of the money) plus its profit; buys were 9.5 percent of the whole account at the "
              f"time, so a sleeve's real size grew and shrank with the account. The grey yardstick is Rs 1,00,000 "
              f"put into the stock on {first_day:%d %b %Y} (the first order) and held, without charges. The "
              f"strategy's first trade came on that day because Historify's candles start on {START} and the "
              f"Supertrend needs 512 hourly candles to warm up.</p>")
    blocks = [
        section("The account", "Account value of the whole strategy, and how far it was below its highest value.", plot("portfolio")),
        section("Profit by stock", "Each stock's profit after charges, closed trades plus any position still held.", plot("profit")),
        section("Equity curve of each stock",
                "Blue: the strategy on the stock, as a Rs 1,00,000 sleeve plus its profit. Grey: Rs 1,00,000 held in "
                "the stock from the first order. Panels in order of profit; each has its own scale.", plot("equity")),
        section("Drawdown of each stock",
                "The fall of each sleeve from its own highest value (blue), against holding the stock (grey). "
                "Same scale in every panel.", plot("drawdown")),
        section("Profit by stock and year", "Rupees made or lost by each stock in each calendar year.", plot("years")),
        section("Monthly returns of the account", "", plot("months")),
        section("Stock statistics", "Sleeve figures are on a Rs 1,00,000 base. Days held is the share of trading "
                "days after the first order that ended with the stock held.", stats_table(stats)),
        f"<section><h2>How these figures are worked out</h2><div class='method'>{method}</div></section>",
    ]
    kpis = portfolio_stats(account, trades, fills, first_day)
    write_page(REPORTS / "custom_tearsheet.html", kpis, blocks)
    stats.to_csv(REPORTS / "stock_stats.csv")
    (CAPITAL / 10 + pnl).round(2).to_csv(REPORTS / "stock_equity.csv")
    print(f"Saved: {REPORTS / 'custom_tearsheet.html'}")
    print(f"       {REPORTS / 'stock_stats.csv'}, {REPORTS / 'stock_equity.csv'}")
