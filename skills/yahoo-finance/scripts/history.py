#!/home/node/.openclaw-env/bin/python3
# SPDX-License-Identifier: MIT
"""
history.py — OHLCV history download with optional data quality validation.

Usage:
    python3 scripts/history.py AAPL --period 1y --interval 1d
    python3 scripts/history.py AAPL --period 6mo --interval 1d --validate --json
    python3 scripts/history.py NVDA --start 2025-01-01 --end 2025-12-31 --json
    python3 scripts/history.py AAPL --period 1y --csv aapl.csv

Periods:   1d 5d 1mo 3mo 6mo 1y 2y 5y 10y ytd max
Intervals: 1m 2m 5m 15m 30m 60m 90m 1h 1d 5d 1wk 1mo 3mo

The Market Data Analyst should always run with --validate. The quality
report includes:
  - gaps           : missing trading-day bars (daily/weekly intervals only)
  - ohlc_violations: bars where High < Low or Close not in [Low, High] etc.
  - duplicate_bars : timestamps appearing twice
  - missing_pct    : pct of expected bars that are missing
"""

import argparse
import sys

from _yf import (
    banner,
    df_to_records,
    emit_error_json,
    emit_json,
    get_ticker_obj,
    now_iso,
    round_num,
)


def fetch_history(symbol: str, period: str, interval: str, start, end):
    t = get_ticker_obj(symbol)
    if start or end:
        df = t.history(start=start, end=end, interval=interval, auto_adjust=False)
    else:
        df = t.history(period=period, interval=interval, auto_adjust=False)
    return df


def validate(df) -> dict:
    """
    Inspect a yfinance OHLCV DataFrame for data quality issues.
    Returns a dict with gaps, ohlc_violations, duplicate_bars, missing_pct.
    """
    pd = __import__("pandas")
    quality = {
        "gaps": [],
        "ohlc_violations": [],
        "duplicate_bars": [],
        "missing_pct": 0.0,
    }
    if df is None or df.empty:
        quality["missing_pct"] = 100.0
        return quality

    # Duplicate bars
    dups = df.index[df.index.duplicated()].tolist()
    quality["duplicate_bars"] = [d.isoformat() for d in dups]

    # OHLC sanity
    for ts, row in df.iterrows():
        try:
            o, h, l, c = (
                float(row["Open"]),
                float(row["High"]),
                float(row["Low"]),
                float(row["Close"]),
            )
        except (KeyError, ValueError, TypeError):
            continue
        if any(x != x for x in (o, h, l, c)):  # NaN check
            continue
        if h < l or o < l or o > h or c < l or c > h:
            quality["ohlc_violations"].append(
                {
                    "date": ts.isoformat(),
                    "open": o,
                    "high": h,
                    "low": l,
                    "close": c,
                }
            )

    # Gap detection — only meaningful for daily/weekly bars on tradable instruments
    if isinstance(df.index, pd.DatetimeIndex) and len(df) > 2:
        # Use business-day frequency as the expected cadence
        try:
            # Strip tz to allow comparison
            idx = df.index.tz_localize(None) if df.index.tz else df.index
            expected = pd.bdate_range(start=idx[0], end=idx[-1])
            actual = pd.DatetimeIndex(idx.normalize().unique())
            missing = expected.difference(actual)
            if len(missing) > 0:
                # Cap to first 50 to keep output bounded
                quality["gaps"] = [d.isoformat() for d in missing[:50]]
                quality["missing_pct"] = round(
                    len(missing) / max(len(expected), 1) * 100, 2
                )
        except Exception:
            pass

    return quality


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download historical OHLCV data with optional quality validation."
    )
    parser.add_argument("ticker", help="Ticker symbol")
    parser.add_argument("--period", default="1y", help="History period (default 1y)")
    parser.add_argument("--interval", default="1d", help="Bar interval (default 1d)")
    parser.add_argument("--start", help="Start date YYYY-MM-DD (overrides --period)")
    parser.add_argument("--end", help="End date YYYY-MM-DD (overrides --period)")
    parser.add_argument(
        "--validate", action="store_true", help="Run data quality checks"
    )
    parser.add_argument(
        "--csv", metavar="PATH", help="Save raw OHLCV to CSV at PATH"
    )
    parser.add_argument("--json", dest="as_json", action="store_true")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="In JSON mode, return only the last N bars (0 = all)",
    )
    args = parser.parse_args()

    try:
        df = fetch_history(args.ticker, args.period, args.interval, args.start, args.end)
    except Exception as e:
        if args.as_json:
            emit_error_json(args.ticker, f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if df is None or df.empty:
        if args.as_json:
            emit_error_json(args.ticker, "Empty history returned")
            sys.exit(0)
        print(f"ERROR: empty history for {args.ticker}", file=sys.stderr)
        sys.exit(1)

    if args.csv:
        df.to_csv(args.csv)

    quality = validate(df) if args.validate else None

    if args.as_json:
        records = df_to_records(df)
        if args.limit > 0:
            records = records[-args.limit :]
        payload = {
            "ticker": args.ticker,
            "period": args.period,
            "interval": args.interval,
            "rows": len(df),
            "range": {
                "start": df.index[0].isoformat() if len(df) else None,
                "end": df.index[-1].isoformat() if len(df) else None,
            },
            "ohlcv": records,
            "fetched_at": now_iso(),
        }
        if quality is not None:
            payload["quality"] = quality
        emit_json(payload)
        sys.exit(0)

    # Human mode
    print(banner(args.ticker))
    print(f"Period: {args.period}  Interval: {args.interval}  Rows: {len(df)}")
    print(f"Range:  {df.index[0]} → {df.index[-1]}")
    print()
    print(df.tail(10).round(4).to_string())
    if quality is not None:
        print()
        print("Quality check:")
        print(f"  duplicate_bars : {len(quality['duplicate_bars'])}")
        print(f"  ohlc_violations: {len(quality['ohlc_violations'])}")
        print(f"  gaps           : {len(quality['gaps'])}")
        print(f"  missing_pct    : {quality['missing_pct']}%")
    if args.csv:
        print(f"\nSaved CSV → {args.csv}")


if __name__ == "__main__":
    main()
