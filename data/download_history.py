"""
download_history.py

Downloads historical candles from your OpenAlgo server in small pieces (the broker
refuses one very long request with "Too many requests"), joins them and saves one
CSV file per symbol and timeframe in this data folder.

Usage (from the "backtesting examples" folder):
    python data/download_history.py --symbol SBIN --exchange NSE --interval 1h --years 5

The API key is read from the .env file in the "backtesting examples" folder
(OPENALGO_API_KEY=...). It is never printed or saved.
"""
import argparse
import os
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from openalgo import api

DATA_DIR = Path(__file__).resolve().parent


def load_env():
    """Read KEY=VALUE lines from the nearest .env file above this script into the environment."""
    for folder in Path(__file__).resolve().parents:
        env_file = folder / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                name, sep, value = line.partition("=")
                if sep and name.strip() and not name.strip().startswith("#"):
                    os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))
            return


def fetch_piece(client, symbol, exchange, interval, start, end, retries=6):
    """Fetch one date range. On a rate-limit error, wait longer each time and try again."""
    wait = 3
    for attempt in range(1, retries + 1):
        result = client.history(symbol=symbol, exchange=exchange, interval=interval,
                                start_date=start.isoformat(), end_date=end.isoformat())
        if isinstance(result, pd.DataFrame):
            return result
        message = str(result.get("message", result)) if isinstance(result, dict) else str(result)
        if "No data" in message:
            return pd.DataFrame()
        print(f"    attempt {attempt} failed ({message.strip()[:80]}), waiting {wait} s")
        time.sleep(wait)
        wait *= 2
    raise RuntimeError(f"could not fetch {start} to {end} after {retries} attempts")


def main():
    parser = argparse.ArgumentParser(description="Download OpenAlgo history in pieces and save it as CSV.")
    parser.add_argument("--symbol", default="SBIN")
    parser.add_argument("--exchange", default="NSE")
    parser.add_argument("--interval", default="1h", help="1m, 3m, 5m, 10m, 15m, 30m, 1h or D")
    parser.add_argument("--years", type=float, default=5, help="years of history to test on")
    parser.add_argument("--warmup-days", type=int, default=180,
                        help="extra calendar days before the test period, so indicators are ready on day one")
    parser.add_argument("--start", default=None,
                        help="first date (YYYY-MM-DD); when given, it replaces --years and --warmup-days")
    parser.add_argument("--end", default=date.today().isoformat(), help="last date (YYYY-MM-DD)")
    parser.add_argument("--chunk-days", type=int, default=90, help="calendar days per request")
    parser.add_argument("--pause", type=float, default=2.0, help="seconds to wait between requests")
    args = parser.parse_args()

    load_env()
    client = api(api_key=os.environ["OPENALGO_API_KEY"],
                 host=os.environ.get("OPENALGO_HOST", "http://127.0.0.1:5000"))

    end = date.fromisoformat(args.end)
    if args.start:
        start = date.fromisoformat(args.start)
    else:
        start = end - timedelta(days=round(args.years * 365.25) + args.warmup_days)
    print(f"Downloading {args.symbol} {args.exchange} {args.interval} from {start} to {end}")

    pieces = []
    piece_start = start
    while piece_start <= end:
        piece_end = min(piece_start + timedelta(days=args.chunk_days - 1), end)
        frame = fetch_piece(client, args.symbol, args.exchange, args.interval, piece_start, piece_end)
        print(f"  {piece_start} to {piece_end}: {len(frame)} candles")
        if len(frame):
            pieces.append(frame)
        piece_start = piece_end + timedelta(days=1)
        time.sleep(args.pause)

    if not pieces:
        raise SystemExit("No candles were returned. Check the symbol, exchange and broker login.")

    bars = pd.concat(pieces)
    bars = bars[~bars.index.duplicated(keep="last")].sort_index()
    bars.index.name = "timestamp"
    columns = [c for c in ("open", "high", "low", "close", "volume", "oi") if c in bars.columns]
    bars = bars[columns]

    path = DATA_DIR / f"{args.symbol}_{args.exchange}_{args.interval}.csv"
    bars.to_csv(path)

    sessions = pd.Series(bars.index.date).nunique()
    print(f"\nSaved {len(bars):,} candles over {sessions:,} sessions to {path}")
    print(f"First candle: {bars.index[0]}   Last candle: {bars.index[-1]}")
    if args.interval not in ("D",):
        times = bars.index.strftime("%H:%M").value_counts().sort_index()
        print("Candles by start time:", times.to_dict())


if __name__ == "__main__":
    main()
