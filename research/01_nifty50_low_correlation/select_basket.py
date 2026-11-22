"""
Research 01: the least correlated NIFTY 50 stocks

Question  : Which NIFTY 50 stocks move least alike, so that a basket of them is as
            diversified as a NIFTY 50 basket can be?
Data      : Daily closes from Historify (source="db"), 22 Nov 2021 to 20 Nov 2026.
            Daily candles are enough for correlation; the 1-minute candles are not needed.
Measure   : Correlation of daily returns (close to close) for every pair of stocks:
            +1 = always move together, 0 = unrelated, -1 = always opposite.
Method    : 1. Start with the stock whose average correlation with the other stocks is lowest.
            2. Add, one at a time, the stock with the lowest average correlation to the
               stocks already chosen, taking at most one stock per sector.
            3. Stop at BASKET_SIZE stocks.
Check     : The same method run on the first three years only (to 21 Nov 2024), then the
            chosen basket's correlation measured on the last two years it never saw.
Cleaning  : One day is left out: TMPV on 14 Oct 2025, the ex-date of the Tata Motors
            demerger, a price drop from the demerger, not from trading. Every other big
            move (the Adani falls of 2023, 4 Jun 2024) is real and stays in.

Run       : python select_basket.py   (from this folder; needs the OpenAlgo server running,
            OPENALGO_API_KEY in the .env file of "backtesting examples", pandas and plotly)
Outputs   : printed report, and in reports/: correlation_report.html (the charts),
            correlation_matrix.csv, average_correlation.csv, basket.csv, out_of_sample.csv
"""
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from openalgo import api

# Where things are
HERE = Path(__file__).resolve().parent
REPORTS = HERE / "reports"

# Settings
START = "2021-11-22"
END = "2026-11-20"
SPLIT = "2024-11-22"   # selection years end the day before; check years start here
BASKET_SIZE = 10       # stocks in the basket
PATH_SIZE = 16         # the basket-size chart goes up to this many stocks (one per sector)

# NIFTY 50 stocks held in Historify, with a broad sector for each (my grouping; NSE's own
# industry names differ in places). Add the 50th constituent here with its sector.
SECTORS = {
    "HDFCBANK": "Banks", "ICICIBANK": "Banks", "SBIN": "Banks", "AXISBANK": "Banks", "KOTAKBANK": "Banks",
    "BAJFINANCE": "Finance and insurance", "BAJAJFINSV": "Finance and insurance",
    "SHRIRAMFIN": "Finance and insurance", "JIOFIN": "Finance and insurance",
    "HDFCLIFE": "Finance and insurance", "SBILIFE": "Finance and insurance",
    "TCS": "IT", "INFY": "IT", "HCLTECH": "IT", "TECHM": "IT",
    "RELIANCE": "Oil, gas and coal", "ONGC": "Oil, gas and coal", "COALINDIA": "Oil, gas and coal",
    "NTPC": "Power", "POWERGRID": "Power",
    "HINDUNILVR": "FMCG", "ITC": "FMCG", "NESTLEIND": "FMCG", "TATACONSUM": "FMCG",
    "MARUTI": "Auto", "M&M": "Auto", "TMPV": "Auto", "BAJAJ-AUTO": "Auto", "EICHERMOT": "Auto",
    "TATASTEEL": "Metals", "JSWSTEEL": "Metals", "HINDALCO": "Metals",
    "SUNPHARMA": "Pharma", "CIPLA": "Pharma", "DRREDDY": "Pharma",
    "APOLLOHOSP": "Hospitals", "MAXHEALTH": "Hospitals",
    "ULTRACEMCO": "Cement and materials", "GRASIM": "Cement and materials",
    "LT": "Capital goods and defence", "BEL": "Capital goods and defence",
    "BHARTIARTL": "Telecom",
    "TITAN": "Consumer and retail", "TRENT": "Consumer and retail",
    "ASIANPAINT": "Consumer and retail", "ETERNAL": "Consumer and retail",
    "ADANIPORTS": "Transport", "INDIGO": "Transport",
    "ADANIENT": "Diversified",
}

# Days whose price change comes from a corporate action, not from trading: left out.
CORPORATE_ACTION_DAYS = [
    ("TMPV", "2025-10-14", "Tata Motors demerger of its commercial vehicle business (ex-date)"),
]

# Chart colours (validated: categorical slots 1 and 2 pass every colour-vision check)
SURFACE, INK, INK_2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, DE_EMPHASIS = "#e1e0d9", "#c3c2b7", "#c3c2b7"
BLUE, ORANGE = "#2a78d6", "#eb6834"
DIVERGING = [[0.0, "#184f95"], [0.25, "#5598e7"], [0.5, "#f0efec"], [0.75, "#e97f7e"], [1.0, "#a8302f"]]
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


# Connect to the OpenAlgo server. The key comes from the .env file, never from this script.
load_env()
client = api(api_key=os.environ["OPENALGO_API_KEY"],
             host=os.environ.get("OPENALGO_HOST", "http://127.0.0.1:5000"))


def daily_closes(symbols):
    """Each stock's daily close from Historify, one column per stock."""
    closes = {}
    for symbol in symbols:
        bars = client.history(symbol=symbol, exchange="NSE", interval="D",
                              start_date=START, end_date=END, source="db")
        if not hasattr(bars, "index"):
            raise SystemExit(f"Historify has no daily candles for {symbol}: {bars}")
        closes[symbol] = bars["close"]
    return pd.DataFrame(closes)


def daily_returns(closes):
    """Close-to-close returns, with the corporate-action days left out."""
    returns = closes.pct_change().iloc[1:]
    for symbol, day, _reason in CORPORATE_ACTION_DAYS:
        if symbol in returns.columns and pd.Timestamp(day) in returns.index:
            returns.loc[pd.Timestamp(day), symbol] = np.nan
    return returns


def average_to_others(corr):
    """Each stock's average correlation with every other stock."""
    n = len(corr)
    return (corr.sum() - 1) / (n - 1)


def average_pair(corr, names):
    """The average correlation over every pair in a group of stocks."""
    sub = corr.loc[names, names].to_numpy()
    upper = sub[np.triu_indices(len(names), k=1)]
    return float(np.nanmean(upper))


def pick_basket(corr, size):
    """Greedy selection: lowest average correlation first, then the stock least correlated
    with the ones already chosen, at most one per sector. Returns the stocks in the order chosen."""
    basket = [average_to_others(corr).idxmin()]
    used = {SECTORS[basket[0]]}
    while len(basket) < size:
        candidates = [s for s in corr.index if s not in basket and SECTORS[s] not in used]
        if not candidates:
            break
        score = corr.loc[candidates, basket].mean(axis=1)
        chosen = score.idxmin()
        basket.append(chosen)
        used.add(SECTORS[chosen])
    return basket


def yearly_volatility(returns):
    """Annualised standard deviation of daily returns (about 248 trading days a year)."""
    return float(returns.std() * np.sqrt(248))


def random_baskets(returns, corr, symbols, size, draws=2000, seed=7):
    """Average pair correlation and equal-weight volatility of random baskets of the same size,
    to show how unusual the chosen basket is. The seed makes the draws the same every run."""
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(draws):
        pick = list(rng.choice(symbols, size=size, replace=False))
        rows.append((average_pair(corr, pick), yearly_volatility(returns[pick].mean(axis=1))))
    return pd.DataFrame(rows, columns=["avg_pair_corr", "volatility"])


# ---------------------------------------------------------------- charts (plotly)

def base_layout(fig, title, subtitle, height):
    fig.update_layout(
        title=dict(text=f"{title}<br><span style='font-size:13px;color:{INK_2}'>{subtitle}</span>",
                   x=0, xanchor="left", font=dict(size=18, color=INK)),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, height=height,
        font=dict(family=FONT, size=12, color=INK_2),
        margin=dict(l=150, r=40, t=90, b=60),
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=AXIS, font=dict(family=FONT, color=INK)),
        legend=dict(orientation="h", x=0, y=1.02, yanchor="bottom", font=dict(color=INK_2)),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont=dict(color=MUTED))
    return fig


def bold_if(names, chosen):
    return [f"<b>{n}</b>" if n in chosen else n for n in names]


def heatmap_all(corr, basket):
    """All stocks, grouped by sector: blocks of red along the diagonal are sectors that move together."""
    order = sorted(corr.index, key=lambda s: (SECTORS[s], s))
    m = corr.loc[order, order]
    labels = bold_if(order, basket)
    hover = [[f"{a} and {b}<br>correlation {m.loc[a, b]:.2f}" for b in order] for a in order]
    fig = go.Figure(go.Heatmap(
        z=m.values, x=labels, y=labels, zmin=-1, zmax=1, zmid=0, colorscale=DIVERGING,
        text=hover, hovertemplate="%{text}<extra></extra>", xgap=1, ygap=1,
        colorbar=dict(title=dict(text="correlation", font=dict(color=INK_2)), tickfont=dict(color=MUTED),
                      outlinewidth=0, thickness=12, len=0.6),
    ))
    # Hairlines between sectors
    sectors = [SECTORS[s] for s in order]
    for i in range(1, len(order)):
        if sectors[i] != sectors[i - 1]:
            for kind in ("x", "y"):
                fig.add_shape(type="line", xref="x" if kind == "x" else "paper",
                              yref="paper" if kind == "x" else "y",
                              x0=i - 0.5 if kind == "x" else 0, x1=i - 0.5 if kind == "x" else 1,
                              y0=0 if kind == "x" else i - 0.5, y1=1 if kind == "x" else i - 0.5,
                              line=dict(color=INK_2, width=1))
    base_layout(fig, "How every pair of NIFTY 50 stocks moved together",
                f"Correlation of daily returns, {START} to {END}. Stocks are grouped by sector; "
                "the basket is in bold. Darker red = more alike, grey = unrelated.", 900)
    fig.update_layout(margin=dict(l=110, r=40, t=90, b=110))
    fig.update_xaxes(tickangle=-60, tickfont=dict(size=10), showgrid=False)
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=10), showgrid=False, scaleanchor="x")
    return fig


def ranked_bars(avg, basket):
    """Each stock's average correlation with the rest, lowest first; the basket highlighted."""
    ranked = avg.sort_values(ascending=False)  # plotly draws the first bar at the bottom
    inside = [s in basket for s in ranked.index]
    fig = go.Figure()
    for flag, name, colour in ((True, "In the basket", BLUE), (False, "Other NIFTY 50 stocks", DE_EMPHASIS)):
        sel = [i for i, f in zip(ranked.index, inside) if f == flag]
        fig.add_trace(go.Bar(
            x=ranked[sel], y=sel, orientation="h", name=name, marker=dict(color=colour),
            text=[f"{v:.2f}" for v in ranked[sel]] if flag else None, textposition="outside",
            textfont=dict(color=INK_2), cliponaxis=False,
            customdata=[SECTORS[s] for s in sel],
            hovertemplate="%{y} (%{customdata})<br>average correlation %{x:.2f}<extra></extra>",
        ))
    base_layout(fig, "Average correlation of each stock with the other NIFTY 50 stocks",
                "Lower = moves less like the rest. The basket takes the lowest, one per sector.",
                40 + 18 * len(ranked) + 150)
    fig.update_layout(barmode="overlay", bargap=0.25, barcornerradius=4)
    fig.update_yaxes(categoryorder="array", categoryarray=list(ranked.index), tickfont=dict(size=11, color=INK_2),
                     showgrid=False)
    fig.update_xaxes(title=dict(text="average correlation with the others", font=dict(color=MUTED)), rangemode="tozero")
    return fig


def size_curve(corr, path, all_pairs, chosen_size):
    """How the basket's average pair correlation rises as stocks are added."""
    sizes = list(range(2, len(path) + 1))
    values = [average_pair(corr, path[:k]) for k in sizes]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sizes, y=values, mode="lines+markers", line=dict(color=BLUE, width=2),
        marker=dict(size=8, color=BLUE, line=dict(color=SURFACE, width=2)),
        customdata=[path[k - 1] for k in sizes],
        hovertemplate="%{x} stocks (last added: %{customdata})<br>average pair correlation %{y:.3f}<extra></extra>",
        showlegend=False,
    ))
    fig.add_hline(y=all_pairs, line=dict(color=MUTED, width=1))
    fig.add_annotation(x=sizes[-1], y=all_pairs, text=f"all NIFTY 50 pairs: {all_pairs:.2f}",
                       showarrow=False, yshift=10, xanchor="right", font=dict(color=INK_2))
    k = chosen_size
    fig.add_annotation(x=k, y=values[k - 2], text=f"chosen: {k} stocks, {values[k - 2]:.2f}",
                       showarrow=True, arrowcolor=MUTED, ax=0, ay=-40, font=dict(color=INK))
    base_layout(fig, "The basket's average pair correlation as stocks are added",
                "Each step adds the stock least correlated with those already chosen, one per sector.", 460)
    fig.update_xaxes(title=dict(text="stocks in the basket", font=dict(color=MUTED)), dtick=1)
    fig.update_yaxes(title=dict(text="average pair correlation", font=dict(color=MUTED)), rangemode="tozero")
    fig.update_layout(margin=dict(l=80, r=40, t=90, b=60))
    return fig


def heatmap_basket(corr, basket):
    """The basket's own correlations, with the numbers in the cells (this is the table view)."""
    m = corr.loc[basket, basket]
    text = [[("" if a == b else f"{m.loc[a, b]:.2f}") for b in basket] for a in basket]
    labels = [f"{s}<br><span style='font-size:10px'>{SECTORS[s]}</span>" for s in basket]
    fig = go.Figure(go.Heatmap(
        z=m.values, x=basket, y=labels, zmin=-1, zmax=1, zmid=0, colorscale=DIVERGING,
        text=text, texttemplate="%{text}", textfont=dict(color=INK, size=12), xgap=2, ygap=2,
        hovertemplate="%{y} and %{x}<br>correlation %{z:.2f}<extra></extra>",
        colorbar=dict(title=dict(text="correlation", font=dict(color=INK_2)), tickfont=dict(color=MUTED),
                      outlinewidth=0, thickness=12, len=0.7),
    ))
    base_layout(fig, f"Correlations inside the {len(basket)}-stock basket",
                "Every pair, in the order the stocks were chosen.", 620)
    fig.update_layout(margin=dict(l=190, r=40, t=90, b=60))
    fig.update_xaxes(showgrid=False, tickfont=dict(color=INK_2))
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(color=INK_2))
    return fig


def out_of_sample_bars(table):
    """The basket picked on the first three years, measured again on the two years after."""
    fig = go.Figure()
    for column, colour in (("Basket picked on the selection years", BLUE), ("All NIFTY 50 pairs", ORANGE)):
        fig.add_trace(go.Bar(
            x=table.index, y=table[column], name=column, marker=dict(color=colour),
            text=[f"{v:.2f}" for v in table[column]], textposition="outside",
            textfont=dict(color=INK_2), cliponaxis=False,
            hovertemplate="%{x}<br>" + column + ": %{y:.3f}<extra></extra>",
        ))
    base_layout(fig, "Did the low correlation last?",
                "Average pair correlation: the basket chosen on the selection years, "
                "then measured on the check years it never saw.", 460)
    fig.update_layout(barmode="group", bargap=0.45, bargroupgap=0.08, barcornerradius=4,
                      margin=dict(l=80, r=40, t=110, b=60))
    fig.update_yaxes(title=dict(text="average pair correlation", font=dict(color=MUTED)), rangemode="tozero")
    fig.update_xaxes(showgrid=False, tickfont=dict(color=INK_2))
    return fig


def random_histogram(rand, basket_value, all_pairs):
    """Where the chosen basket sits among random baskets of the same size."""
    fig = go.Figure(go.Histogram(
        x=rand["avg_pair_corr"], nbinsx=40, marker=dict(color=DE_EMPHASIS, line=dict(color=SURFACE, width=1)),
        hovertemplate="average pair correlation %{x}<br>%{y} random baskets<extra></extra>", showlegend=False,
    ))
    fig.add_vline(x=basket_value, line=dict(color=BLUE, width=2))
    fig.add_annotation(x=basket_value, y=1, yref="paper", text=f"chosen basket {basket_value:.2f}",
                       showarrow=False, xanchor="left", xshift=6, font=dict(color=INK))
    fig.add_vline(x=all_pairs, line=dict(color=MUTED, width=1))
    fig.add_annotation(x=all_pairs, y=0.92, yref="paper", text=f"all NIFTY 50 pairs {all_pairs:.2f}",
                       showarrow=False, xanchor="left", xshift=6, font=dict(color=INK_2))
    base_layout(fig, f"The chosen basket against {len(rand):,} random baskets of {BASKET_SIZE} stocks",
                "Average pair correlation of each random basket. Further left = less alike.", 440)
    fig.update_layout(bargap=0.04, margin=dict(l=80, r=40, t=90, b=60))
    fig.update_xaxes(title=dict(text="average pair correlation", font=dict(color=MUTED)))
    fig.update_yaxes(title=dict(text="random baskets", font=dict(color=MUTED)))
    return fig


def write_report(figures, path):
    """All charts in one HTML file that opens offline in any browser."""
    parts = [f"<html><head><meta charset='utf-8'><title>NIFTY 50 correlation</title>"
             f"<style>body{{background:{SURFACE};color:{INK};font-family:{FONT};max-width:1100px;"
             f"margin:24px auto;padding:0 16px}} .chart{{margin:28px 0 44px}}</style></head><body>"
             f"<h1 style='font-size:24px'>Least correlated NIFTY 50 stocks</h1>"
             f"<p style='color:{INK_2}'>Daily returns from Historify, {START} to {END}. "
             f"Hover over any chart to read its values; the CSV files beside this page hold every number.</p>"]
    for i, fig in enumerate(figures):
        parts.append("<div class='chart'>" + fig.to_html(full_html=False, include_plotlyjs=(i == 0),
                                                       config={"displaylogo": False}) + "</div>")
    parts.append("</body></html>")
    path.write_text("".join(parts), encoding="utf-8")


if __name__ == "__main__":
    REPORTS.mkdir(exist_ok=True)
    symbols = list(SECTORS)
    closes = daily_closes(symbols)
    returns = daily_returns(closes)
    print(f"{len(symbols)} stocks, {len(returns)} trading days, {START} to {END}")
    short = closes.notna().sum()
    for s in short[short < short.max()].index:
        print(f"  {s} has {short[s]} days (listed {closes[s].first_valid_index().date()}); its pairs use the days it traded")

    # 1. Correlation over the five years
    corr = returns.corr()
    avg = average_to_others(corr)
    all_pairs = average_pair(corr, symbols)
    basket = pick_basket(corr, BASKET_SIZE)
    path = pick_basket(corr, PATH_SIZE)
    print(f"\nAverage correlation over all {len(symbols) * (len(symbols) - 1) // 2} pairs: {all_pairs:.3f}")
    print("Lowest average correlation:", ", ".join(f"{s} {v:.2f}" for s, v in avg.nsmallest(5).items()))
    print("Highest average correlation:", ", ".join(f"{s} {v:.2f}" for s, v in avg.nlargest(5).items()))

    print(f"\n== The {BASKET_SIZE}-stock basket (in the order chosen)")
    rows = []
    for i, s in enumerate(basket, 1):
        others = [b for b in basket if b != s]
        rows.append({"order": i, "symbol": s, "sector": SECTORS[s],
                     "avg_corr_to_nifty50": round(avg[s], 3),
                     "avg_corr_to_basket": round(corr.loc[s, others].mean(), 3),
                     "highest_pair_in_basket": f"{corr.loc[s, others].idxmax()} {corr.loc[s, others].max():.2f}"})
    basket_table = pd.DataFrame(rows).set_index("order")
    print(basket_table.to_string())
    basket_pairs = average_pair(corr, basket)
    print(f"Basket average pair correlation: {basket_pairs:.3f} (all NIFTY 50 pairs: {all_pairs:.3f})")

    # 2. Daily swings of an equal-weight basket against an equal-weight NIFTY 50 (rebalanced daily),
    #    and against random baskets of the same size
    vol_basket = yearly_volatility(returns[basket].mean(axis=1))
    vol_all = yearly_volatility(returns[symbols].mean(axis=1))
    vol_single = float(np.median([yearly_volatility(returns[s].dropna()) for s in basket]))
    vol_single_all = float(np.median([yearly_volatility(returns[s].dropna()) for s in symbols]))
    rand = random_baskets(returns, corr, symbols, BASKET_SIZE)
    corr_rank = float((rand["avg_pair_corr"] < basket_pairs).mean())
    vol_rank = float((rand["volatility"] < vol_basket).mean())
    print(f"\nYearly volatility, equal weight: basket {vol_basket:.2%}, all {len(symbols)} stocks {vol_all:.2%}, "
          f"random {BASKET_SIZE}-stock baskets (median) {rand['volatility'].median():.2%}")
    print(f"A single stock on its own (median): basket stocks {vol_single:.2%}, all stocks {vol_single_all:.2%}")
    print(f"Random {BASKET_SIZE}-stock baskets with a lower average pair correlation than the basket: {corr_rank:.1%}; "
          f"with lower volatility: {vol_rank:.1%}")

    # Context: a different asset class. GOLDBEES against every NIFTY 50 stock.
    gold = client.history(symbol="GOLDBEES", exchange="NSE", interval="D",
                          start_date=START, end_date=END, source="db")["close"].pct_change().iloc[1:]
    gold_corr = returns.corrwith(gold)
    print(f"GOLDBEES (gold ETF) average correlation with the {len(symbols)} stocks: {gold_corr.mean():.3f} "
          f"(range {gold_corr.min():.2f} to {gold_corr.max():.2f})")

    # 3. Out of sample: pick on the selection years, measure on the check years
    sel, chk = returns.loc[:pd.Timestamp(SPLIT) - pd.Timedelta(days=1)], returns.loc[SPLIT:]
    corr_sel, corr_chk = sel.corr(), chk.corr()
    basket_sel = pick_basket(corr_sel, BASKET_SIZE)
    sel_label = f"Selection years ({sel.index[0].date()} to {sel.index[-1].date()})"
    chk_label = f"Check years ({chk.index[0].date()} to {chk.index[-1].date()})"
    oos = pd.DataFrame({
        "Basket picked on the selection years": [average_pair(corr_sel, basket_sel), average_pair(corr_chk, basket_sel)],
        "All NIFTY 50 pairs": [average_pair(corr_sel, symbols), average_pair(corr_chk, symbols)],
    }, index=[sel_label, chk_label])
    print("\n== Out of sample")
    print("Basket picked on the selection years:", ", ".join(basket_sel))
    print("Same stocks as the five-year basket:", ", ".join(s for s in basket_sel if s in basket) or "none")
    print(oos.round(3).to_string())

    # 4. Files
    corr.round(4).to_csv(REPORTS / "correlation_matrix.csv")
    avg.sort_values().round(4).rename("avg_corr_to_others").to_frame().assign(
        sector=lambda d: [SECTORS[s] for s in d.index]).to_csv(REPORTS / "average_correlation.csv")
    basket_table.to_csv(REPORTS / "basket.csv")
    oos.round(4).to_csv(REPORTS / "out_of_sample.csv")
    rand.round(4).to_csv(REPORTS / "random_baskets.csv", index_label="draw")
    figures = [
        ranked_bars(avg, basket),
        size_curve(corr, path, all_pairs, BASKET_SIZE),
        random_histogram(rand, basket_pairs, all_pairs),
        heatmap_basket(corr, basket),
        out_of_sample_bars(oos),
        heatmap_all(corr, basket),
    ]
    write_report(figures, REPORTS / "correlation_report.html")

    # 5. Every number the shareable page (page_template.html) needs, then the page itself
    order = sorted(symbols, key=lambda s: (SECTORS[s], s))
    data = {
        "start": START, "end": END, "days": len(returns), "split": SPLIT,
        "selection_years": [str(sel.index[0].date()), str(sel.index[-1].date())],
        "check_years": [str(chk.index[0].date()), str(chk.index[-1].date())],
        "stocks": len(symbols), "pairs": len(symbols) * (len(symbols) - 1) // 2,
        "basket_size": BASKET_SIZE, "sectors": SECTORS, "order": order,
        "corr": corr.loc[order, order].round(3).values.tolist(),
        "avg": {s: round(float(v), 4) for s, v in avg.items()},
        "all_pairs": round(all_pairs, 4), "basket": basket, "basket_pairs": round(basket_pairs, 4),
        "basket_rows": basket_table.reset_index().to_dict(orient="records"),
        "path": path, "path_values": [round(average_pair(corr, path[:k]), 4) for k in range(2, len(path) + 1)],
        "random_avg_pair": rand["avg_pair_corr"].round(4).tolist(),
        "random_corr_share_lower": round(corr_rank, 4), "random_vol_share_lower": round(vol_rank, 4),
        "vol_basket": round(vol_basket, 4), "vol_all": round(vol_all, 4),
        "vol_random_median": round(float(rand["volatility"].median()), 4),
        "vol_single_basket": round(vol_single, 4), "vol_single_all": round(vol_single_all, 4),
        "basket_sel": basket_sel, "oos": {
            "labels": ["Selection years", "Check years"],
            "basket": [round(v, 4) for v in oos.iloc[:, 0]], "all": [round(v, 4) for v in oos.iloc[:, 1]],
        },
        "gold_avg": round(float(gold_corr.mean()), 3), "gold_min": round(float(gold_corr.min()), 2),
        "gold_max": round(float(gold_corr.max()), 2),
        "lowest5": [[s, round(float(v), 3)] for s, v in avg.nsmallest(5).items()],
        "highest5": [[s, round(float(v), 3)] for s, v in avg.nlargest(5).items()],
        "jiofin_days": int(closes["JIOFIN"].notna().sum()) if "JIOFIN" in closes else None,
        "corporate_actions": [list(x) for x in CORPORATE_ACTION_DAYS],
    }
    template = (HERE / "page_template.html").read_text(encoding="utf-8")
    page = template.replace("__DATA__", json.dumps(data, separators=(",", ":")))
    (REPORTS / "correlation_page.html").write_text(page, encoding="utf-8")
    print(f"\nSaved: {REPORTS / 'correlation_report.html'} (Plotly charts, opens offline)")
    print(f"       {REPORTS / 'correlation_page.html'} (the shareable page)")
    print(f"       {REPORTS / 'correlation_matrix.csv'}, average_correlation.csv, basket.csv, "
          "out_of_sample.csv, random_baskets.csv")
