"""
Strategy 05: candle charts with every buy and sell signal, drawn with OpenAlgo Charts

Reads the files strategy.py wrote in reports/ (signals.csv, trades.csv, open_positions.csv,
by_stock.csv, compared.csv, tables/fills.csv) and writes one page, reports/signal_charts.html,
that opens in any browser without an internet connection.

For each of the 8 stocks the page shows:
  * the hourly candles of the test (1 Apr 2022 to 20 Nov 2026), from Historify
  * the strategy's line: the UT Bot trailing stop, or the Supertrend line, green while the
    close is above it and red while it is below
  * the signals: B under the candle whose close gave a buy signal, S over the candle
    whose close gave a sell signal
  * the fills: a blue dot where a buy filled (the next candle's open), an orange dot
    where a sell filled
  * the stock's trades as a table; click a row to zoom the chart to that trade

The library is OpenAlgo Charts 2.7.3 (Apache-2.0), its browser build kept in
vendor/openalgo-charts-2.7.3/ and written into the page. If that file is missing it is
downloaded once from the pinned unpkg address and checked against its SHA-256.

Run       : python charts.py   (from this folder, after python strategy.py)
"""
import hashlib
import json
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPORTS = HERE / "reports"
LIB_VERSION = "2.7.3"
LIB = HERE / "vendor" / f"openalgo-charts-{LIB_VERSION}" / "openalgo-charts.standalone.js"
LIB_URL = f"https://unpkg.com/openalgo-charts@{LIB_VERSION}/dist/openalgo-charts.standalone.js"
LIB_SHA256 = "367ab4ab02c6ffb1847158feebbd1faa9f4b3f973d27a566f66678769a4efe82"

GROUPS = [
    {"key": "UTBotBasket", "name": "UT Bot", "share": "60%, Rs 6,00,000",
     "line": "UT Bot trailing stop (key value 1, ATR 10)",
     "symbols": ["SBIN", "RELIANCE", "MAXHEALTH", "CIPLA"]},
    {"key": "SupertrendBasket", "name": "Supertrend", "share": "40%, Rs 4,00,000",
     "line": "Supertrend (ATR 10, multiplier 3)",
     "symbols": ["SUNPHARMA", "ICICIBANK", "TATASTEEL", "MARUTI"]},
]


def library():
    """The OpenAlgo Charts browser build: the kept copy, or a checked download of it."""
    if not LIB.exists():
        LIB.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(LIB_URL, timeout=60) as response:
            LIB.write_bytes(response.read())
    code = LIB.read_bytes()
    if hashlib.sha256(code).hexdigest() != LIB_SHA256:
        raise SystemExit(f"{LIB} is not the expected openalgo-charts {LIB_VERSION} build (SHA-256 differs)")
    return code.decode("utf-8")


def epoch(values):
    """IST times (text with +05:30, or naive IST) as UTC seconds, the time unit of the chart."""
    stamps = pd.to_datetime(pd.Series(values))
    if stamps.dt.tz is None:
        stamps = stamps.dt.tz_localize("Asia/Kolkata")
    return (stamps.dt.tz_convert("UTC").astype("int64") // 10**9).to_numpy()


def ist_text(values):
    stamps = pd.to_datetime(pd.Series(values))
    if stamps.dt.tz is None:
        stamps = stamps.dt.tz_localize("Asia/Kolkata")
    return stamps.dt.tz_convert("Asia/Kolkata").dt.strftime("%d %b %Y %H:%M").tolist()


def snap(bar_times, times):
    """Each time moved to the open of the candle it falls in (a special session's fill can
    come a few minutes after the candle's open)."""
    idx = np.searchsorted(bar_times, times, side="right") - 1
    return bar_times[np.clip(idx, 0, len(bar_times) - 1)]


def r2(values):
    return [None if pd.isna(v) else round(float(v), 2) for v in values]


def symbol_data(s, signals, trades, still, fills, stocks):
    f = signals[signals["symbol"] == s].sort_index()
    t = epoch(f.index)
    side = f["side"].isin(["above", "green"]).astype(int).tolist()
    sig = f[f["signal"] != ""]
    sig_t = epoch(sig.index)

    rows = []
    tr = trades[trades["symbol"] == s]
    entry_t, exit_t = epoch(tr["entry_time"]), epoch(tr["exit_time"])
    for i, (_, row) in enumerate(tr.iterrows()):
        rows.append({
            "n": int(row["trade"]), "in": int(snap(t, [entry_t[i]])[0]), "out": int(snap(t, [exit_t[i]])[0]),
            "in_text": ist_text([row["entry_time"]])[0], "out_text": ist_text([row["exit_time"]])[0],
            "qty": int(row["quantity"]), "in_px": round(float(row["entry_price"]), 2),
            "out_px": round(float(row["exit_price"]), 2), "pnl": round(float(row["net_pnl"]), 2),
            "ret": round(float(row["return_pct"]), 2),
        })
    held = still[(still["symbol"] == s) & (still["quantity_units"] != 0)]
    if len(held):
        buys = fills[(fills["symbol"] == s) & (fills["side"] == "BUY")]
        last = buys.iloc[-1]
        h = held.iloc[0]
        rows.append({
            "n": None, "in": int(snap(t, epoch([last["time"]]))[0]), "out": None,
            "in_text": ist_text([last["time"]])[0], "out_text": "still held",
            "qty": int(h["quantity_units"]), "in_px": round(float(h["average_price_rupees"]), 2),
            "out_px": round(float(h["mark_rupees"]), 2), "pnl": round(float(h["unrealized_rupees"]), 2),
            "ret": None,
        })

    st = stocks.loc[s]
    return {
        "t": t.tolist(), "o": r2(f["open"]), "h": r2(f["high"]), "l": r2(f["low"]), "c": r2(f["close"]),
        "line": r2(f["line"]), "side": side,
        "signals": [[int(x), kind] for x, kind in zip(sig_t, sig["signal"])],
        "trades": rows,
        "stats": {
            "closed_trades": int(st["closed_trades"]),
            "win_rate": None if pd.isna(st["win_rate"]) else float(st["win_rate"]),
            "total_pnl": float(st["total_pnl"]), "open_pnl": float(st["open_pnl"]),
            "charges": float(st["charges"]), "stock_return": float(st["stock_return_buy_hold"]),
            "buy_signals": int((sig["signal"] == "buy").sum()), "sell_signals": int((sig["signal"] == "sell").sum()),
        },
    }


def summary_rows(compared):
    names = {
        "Strategy 05 account (UT Bot 60% + Supertrend 40%)": "Account, both strategies",
        "  UT Bot on Rs 6 lakh": "UT Bot, Rs 6 lakh",
        "  Supertrend on Rs 4 lakh": "Supertrend, Rs 4 lakh",
        "Same 8 stocks, same 60:40 money, bought and held": "Same 8 stocks held",
        "NIFTYBEES, Rs 10 lakh bought and held": "NIFTYBEES held",
    }
    out = []
    for key, label in names.items():
        if key in compared.index:
            r = compared.loc[key]
            out.append({"label": label, "net": float(r["net_profit"]), "ret": float(r["total_return"]),
                        "cagr": float(r["cagr"]), "dd": float(r["max_drawdown"])})
    return out


def main():
    signals = pd.read_csv(REPORTS / "signals.csv", index_col="time", keep_default_na=False,
                          na_values=[""], dtype={"signal": str, "want": str})
    signals["signal"] = signals["signal"].fillna("")
    trades = pd.read_csv(REPORTS / "trades.csv")
    still = pd.read_csv(REPORTS / "open_positions.csv")
    fills = pd.read_csv(REPORTS / "tables" / "fills.csv")
    stocks = pd.read_csv(REPORTS / "by_stock.csv", index_col="symbol")
    compared = pd.read_csv(REPORTS / "compared.csv", index_col=0)

    data = {
        "period": f"{signals.index.min()[:10]} to {signals.index.max()[:10]}",
        "groups": [{k: g[k] for k in ("key", "name", "share", "line", "symbols")} for g in GROUPS],
        "summary": summary_rows(compared),
        "symbols": {s: symbol_data(s, signals, trades, still, fills, stocks)
                    for g in GROUPS for s in g["symbols"]},
    }
    page = (PAGE.replace("__LIB__", library())
                .replace("__DATA__", json.dumps(data, separators=(",", ":")).replace("</", "<\\/")))
    out = REPORTS / "signal_charts.html"
    out.write_text(page, encoding="utf-8")
    print(f"Saved: {out} ({out.stat().st_size / 1e6:.1f} MB)")


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Strategy 05 Signal Charts</title>
<style>
/* Layout: a header with the account's result, a stock picker grouped by strategy, then the
   chart and the stock's trades. */
:root {
  --bg: #f7f7f5; --panel: #ffffff; --ink: #16181d; --ink-2: #4c5160; --muted: #808594;
  --line: #e2e3e7; --accent: #2a78d6; --up: #1b9e6f; --down: #d9433f; --exit: #eb6834;
  --font: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --mono: ui-monospace, "Cascadia Mono", Consolas, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #0f1115; --panel: #171a21; --ink: #e9eaee; --ink-2: #b4b8c4; --muted: #868b99;
  --line: #2a2e38; --accent: #5b9cf0; --up: #2fbf87; --down: #f0605b; --exit: #f08a5d; color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #0f1115; --panel: #171a21; --ink: #e9eaee; --ink-2: #b4b8c4; --muted: #868b99;
  --line: #2a2e38; --accent: #5b9cf0; --up: #2fbf87; --down: #f0605b; --exit: #f08a5d; color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 14px/1.45 var(--font); }
.wrap { max-width: 1280px; margin: 0 auto; padding: 20px 16px 40px; display: grid; gap: 16px; }
header { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px; align-items: flex-start; }
h1 { font-size: 22px; margin: 0; letter-spacing: -0.01em; }
.sub { color: var(--ink-2); margin-top: 2px; }
button { font: inherit; color: var(--ink); background: var(--panel); border: 1px solid var(--line);
  border-radius: 6px; padding: 5px 10px; cursor: pointer; }
button:hover { border-color: var(--muted); }
button:focus-visible, input:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.summary { display: flex; flex-wrap: wrap; gap: 8px; }
.sum { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 8px 12px; min-width: 0; }
.sum .k { font-size: 12px; color: var(--muted); }
.sum .v { font-variant-numeric: tabular-nums; font-weight: 600; }
.sum .s { font-size: 12px; color: var(--ink-2); font-variant-numeric: tabular-nums; }
.picker { display: flex; flex-wrap: wrap; gap: 16px; }
.group { display: grid; gap: 6px; }
.group .gname { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); }
.group .row { display: flex; flex-wrap: wrap; gap: 6px; }
.sym[aria-pressed="true"] { background: var(--accent); border-color: var(--accent); color: #fff; }
.bar { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; justify-content: space-between; }
.stats { display: flex; flex-wrap: wrap; gap: 18px; font-variant-numeric: tabular-nums; }
.stats div span { display: block; font-size: 12px; color: var(--muted); }
.stats b { font-weight: 600; }
.pos { color: var(--up); } .neg { color: var(--down); }
.controls { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; color: var(--ink-2); }
.controls label { display: inline-flex; gap: 5px; align-items: center; cursor: pointer; }
.chartbox { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
#chart { width: 100%; height: 560px; }
.legend { display: flex; flex-wrap: wrap; gap: 16px; font-size: 12px; color: var(--ink-2); }
.legend i { display: inline-block; vertical-align: middle; margin-right: 5px; }
.sw-line { width: 18px; height: 3px; border-radius: 2px; }
.sw-dot { width: 9px; height: 9px; border-radius: 50%; }
.tablebox { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; max-height: 380px; overflow: auto; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
th, td { padding: 6px 10px; text-align: right; white-space: nowrap; border-bottom: 1px solid var(--line); }
th { position: sticky; top: 0; background: var(--panel); color: var(--muted); font-weight: 600; font-size: 12px; }
th:nth-child(2), td:nth-child(2), th:nth-child(4), td:nth-child(4) { text-align: left; }
tbody tr { cursor: pointer; }
tbody tr:hover { background: color-mix(in srgb, var(--accent) 8%, transparent); }
tbody tr.on { background: color-mix(in srgb, var(--accent) 16%, transparent); }
.note { font-size: 12px; color: var(--muted); }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>Strategy 05: UT Bot and Supertrend, hourly, long only</h1>
      <div class="sub" id="period"></div>
    </div>
    <button type="button" id="theme">Dark</button>
  </header>
  <div class="summary" id="summary"></div>
  <div class="picker" id="picker"></div>
  <div class="bar">
    <div class="stats" id="stats"></div>
    <div class="controls">
      <label><input type="checkbox" id="show-signals" checked> Signals</label>
      <label><input type="checkbox" id="show-fills" checked> Fills</label>
      <button type="button" id="recent">Last 300 candles</button>
      <button type="button" id="all">All</button>
    </div>
  </div>
  <div class="chartbox"><div id="chart"></div></div>
  <div class="legend" id="legend"></div>
  <div class="tablebox">
    <table>
      <thead><tr><th>#</th><th>Bought</th><th>Price</th><th>Sold</th><th>Price</th><th>Shares</th><th>Net P&amp;L (Rs)</th><th>Return</th></tr></thead>
      <tbody id="trades"></tbody>
    </table>
  </div>
  <div class="note">Signals are worked out from the closed hourly candle; each order fills at the open of the next candle, a signal on the day's last candle at 09:15 the next day. P&amp;L is after charges and slippage. Click a trade to zoom to it.</div>
</div>
<script>__LIB__</script>
<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  "use strict";
  var OAC = window.OpenAlgoCharts;
  var DATA = JSON.parse(document.getElementById("data").textContent);
  var root = document.documentElement;
  var el = document.getElementById("chart");
  var chart = null, candles = null, markers = null, current = null;

  function css(name) { return getComputedStyle(root).getPropertyValue(name).trim(); }
  function dark() {
    var t = root.getAttribute("data-theme");
    return t ? t === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
  }
  function rupees(v) { return (v < 0 ? "-" : "") + "Rs " + Math.abs(v).toLocaleString("en-IN", {maximumFractionDigits: 0}); }
  function pct(v) { return (v * 100).toFixed(2) + "%"; }
  function cls(v) { return v >= 0 ? "pos" : "neg"; }

  document.getElementById("period").textContent =
    "Rs 10,00,000 split 60:40, hourly candles from Historify, " + DATA.period + ". Fills at the next candle's open, Zerodha charges, 2 bps slippage.";

  document.getElementById("summary").innerHTML = DATA.summary.map(function (r) {
    return '<div class="sum"><div class="k">' + r.label + '</div><div class="v ' + cls(r.net) + '">' + rupees(r.net) +
      '</div><div class="s">' + pct(r.ret) + " total, " + pct(r.cagr) + " a year, worst fall " + pct(r.dd) + "</div></div>";
  }).join("");

  var picker = document.getElementById("picker");
  DATA.groups.forEach(function (g) {
    var box = document.createElement("div");
    box.className = "group";
    box.innerHTML = '<div class="gname">' + g.name + " (" + g.share + ")</div>";
    var row = document.createElement("div");
    row.className = "row";
    g.symbols.forEach(function (s) {
      var b = document.createElement("button");
      b.type = "button"; b.className = "sym"; b.textContent = s; b.dataset.symbol = s;
      b.setAttribute("aria-pressed", "false");
      b.addEventListener("click", function () { show(s); });
      row.appendChild(b);
    });
    box.appendChild(row);
    picker.appendChild(box);
  });

  function groupOf(s) { return DATA.groups.filter(function (g) { return g.symbols.indexOf(s) >= 0; })[0]; }

  function markerList(d) {
    var list = [];
    if (document.getElementById("show-signals").checked) {
      d.signals.forEach(function (x) {
        list.push(x[1] === "buy"
          ? {time: x[0], position: "belowBar", shape: "arrowUp", size: "small", color: css("--up"), text: "B"}
          : {time: x[0], position: "aboveBar", shape: "arrowDown", size: "small", color: css("--down"), text: "S"});
      });
    }
    if (document.getElementById("show-fills").checked) {
      d.trades.forEach(function (tr) {
        list.push({time: tr.in, position: "atPrice", price: tr.in_px, shape: "circle", size: "small", color: css("--accent")});
        if (tr.out !== null) list.push({time: tr.out, position: "atPrice", price: tr.out_px, shape: "circle", size: "small", color: css("--exit")});
      });
    }
    list.sort(function (a, b) { return a.time - b.time; });
    return list;
  }

  function indexOf(d, t) {
    var lo = 0, hi = d.t.length - 1;
    while (lo < hi) { var mid = (lo + hi + 1) >> 1; if (d.t[mid] <= t) lo = mid; else hi = mid - 1; }
    return lo;
  }

  function recent() {
    var n = current.t.length;
    chart.setVisibleLogicalRange({from: Math.max(0, n - 300), to: n + 3});
  }

  function build(s) {
    var d = DATA.symbols[s];
    current = d;
    if (chart) chart.destroy();
    chart = OAC.createChart(el, {timezone: "Asia/Kolkata", theme: dark() ? OAC.darkTheme : OAC.lightTheme});
    candles = chart.addSeries("candlestick");
    var bars = new Array(d.t.length), up = new Array(d.t.length), down = new Array(d.t.length);
    for (var i = 0; i < d.t.length; i++) {
      var t = d.t[i];
      bars[i] = {time: t, open: d.o[i], high: d.h[i], low: d.l[i], close: d.c[i]};
      var v = d.line[i];
      if (v === null) { up[i] = {time: t}; down[i] = {time: t}; }
      else if (d.side[i] === 1) { up[i] = {time: t, value: v}; down[i] = {time: t}; }
      else { down[i] = {time: t, value: v}; up[i] = {time: t}; }
    }
    candles.setData(bars);
    var style = {lineWidth: 2, priceLineVisible: false, lastValueVisible: false};
    chart.addSeries("line", {style: Object.assign({color: css("--up")}, style)}).setData(up);
    chart.addSeries("line", {style: Object.assign({color: css("--down")}, style)}).setData(down);
    markers = candles.createMarkers();
    markers.setMarkers(markerList(d));
    recent();
  }

  function stats(s) {
    var st = DATA.symbols[s].stats, g = groupOf(s);
    document.getElementById("stats").innerHTML =
      "<div><span>" + g.name + "</span><b>" + s + "</b></div>" +
      "<div><span>Closed trades</span><b>" + st.closed_trades + "</b></div>" +
      "<div><span>Won</span><b>" + (st.win_rate === null ? "n/a" : Math.round(st.win_rate * 100) + "%") + "</b></div>" +
      '<div><span>Profit after charges</span><b class="' + cls(st.total_pnl) + '">' + rupees(st.total_pnl) + "</b></div>" +
      "<div><span>Charges</span><b>" + rupees(st.charges) + "</b></div>" +
      '<div><span>The stock itself</span><b class="' + cls(st.stock_return) + '">' + pct(st.stock_return) + "</b></div>" +
      "<div><span>Signals</span><b>" + st.buy_signals + " B, " + st.sell_signals + " S</b></div>";
    document.getElementById("legend").innerHTML =
      '<span><i class="sw-line" style="background:var(--up)"></i>' + g.line + ", close above it</span>" +
      '<span><i class="sw-line" style="background:var(--down)"></i>close below it</span>' +
      '<span><b style="color:var(--up)">B</b> buy signal candle</span>' +
      '<span><b style="color:var(--down)">S</b> sell signal candle</span>' +
      '<span><i class="sw-dot" style="background:var(--accent)"></i>buy filled</span>' +
      '<span><i class="sw-dot" style="background:var(--exit)"></i>sell filled</span>';
  }

  function table(s) {
    var body = document.getElementById("trades");
    body.innerHTML = "";
    DATA.symbols[s].trades.slice().reverse().forEach(function (tr) {
      var row = document.createElement("tr");
      var cells = [tr.n === null ? "open" : tr.n, tr.in_text, tr.in_px.toFixed(2), tr.out_text,
        tr.out_px.toFixed(2), tr.qty, rupees(tr.pnl), tr.ret === null ? "" : tr.ret.toFixed(2) + "%"];
      cells.forEach(function (c, i) {
        var td = document.createElement("td");
        td.textContent = c;
        if (i === 6) td.className = cls(tr.pnl);
        row.appendChild(td);
      });
      row.addEventListener("click", function () {
        Array.prototype.forEach.call(body.children, function (r) { r.classList.remove("on"); });
        row.classList.add("on");
        var a = indexOf(current, tr.in), b = tr.out === null ? current.t.length - 1 : indexOf(current, tr.out);
        var pad = Math.max(30, Math.round((b - a) * 0.6));
        chart.setVisibleLogicalRange({from: Math.max(0, a - pad), to: b + pad});
        el.scrollIntoView({behavior: "smooth", block: "center"});
      });
      body.appendChild(row);
    });
  }

  function show(s) {
    Array.prototype.forEach.call(document.querySelectorAll(".sym"), function (b) {
      b.setAttribute("aria-pressed", b.dataset.symbol === s ? "true" : "false");
    });
    build(s); stats(s); table(s);
  }

  ["show-signals", "show-fills"].forEach(function (id) {
    document.getElementById(id).addEventListener("change", function () { markers.setMarkers(markerList(current)); });
  });
  document.getElementById("recent").addEventListener("click", recent);
  document.getElementById("all").addEventListener("click", function () { chart.fitContent(); });

  var themeButton = document.getElementById("theme");
  function themeLabel() { themeButton.textContent = dark() ? "Light" : "Dark"; }
  themeButton.addEventListener("click", function () {
    root.setAttribute("data-theme", dark() ? "light" : "dark");
    themeLabel();
    chart.setTheme(dark() ? OAC.darkTheme : OAC.lightTheme);
    var range = chart.getVisibleLogicalRange();
    var s = document.querySelector('.sym[aria-pressed="true"]').dataset.symbol;
    build(s);
    chart.setVisibleLogicalRange(range);
  });
  themeLabel();
  show(DATA.groups[0].symbols[0]);
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
