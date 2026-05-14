#!/home/node/.openclaw-env/bin/python3
# SPDX-License-Identifier: MIT
"""
options.py — options chain (calls + puts) for an expiration.

Usage:
    python3 scripts/options.py SPY --list-expirations
    python3 scripts/options.py SPY --expiration 2026-04-17 --json
    python3 scripts/options.py AAPL --json    # picks first expiration

If neither --list-expirations nor --expiration is given, defaults to the
nearest expiration.
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
    safe_num,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Options chain for a ticker.")
    parser.add_argument("ticker")
    parser.add_argument("--list-expirations", action="store_true")
    parser.add_argument("--expiration", help="Expiration date YYYY-MM-DD")
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args()

    try:
        t = get_ticker_obj(args.ticker)
        expirations = list(t.options) if t.options else []
    except Exception as e:
        if args.as_json:
            emit_error_json(args.ticker, f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if not expirations:
        msg = "No options listed for this ticker"
        if args.as_json:
            emit_error_json(args.ticker, msg)
            sys.exit(0)
        print(f"ERROR: {msg}", file=sys.stderr)
        sys.exit(1)

    if args.list_expirations:
        if args.as_json:
            emit_json({"ticker": args.ticker, "expirations": expirations, "fetched_at": now_iso()})
        else:
            print(banner(args.ticker))
            print(f"Expirations ({len(expirations)}):")
            for e in expirations:
                print(f"  {e}")
        sys.exit(0)

    target = args.expiration or expirations[0]
    if target not in expirations:
        msg = f"Expiration {target} not available. Choose from: {expirations[:5]}..."
        if args.as_json:
            emit_error_json(args.ticker, msg)
            sys.exit(0)
        print(f"ERROR: {msg}", file=sys.stderr)
        sys.exit(1)

    try:
        chain = t.option_chain(target)
        underlying = None
        try:
            fi = t.fast_info
            underlying = safe_num(fi["last_price"]) if fi else None
        except Exception:
            underlying = None
    except Exception as e:
        if args.as_json:
            emit_error_json(args.ticker, f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    def slim(df):
        if df is None or df.empty:
            return []
        cols = [c for c in ("strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility", "inTheMoney") if c in df.columns]
        return df_to_records(df[cols])

    payload = {
        "ticker": args.ticker,
        "expiration": target,
        "underlying_price": underlying,
        "calls": slim(chain.calls),
        "puts": slim(chain.puts),
        "fetched_at": now_iso(),
    }

    if args.as_json:
        emit_json(payload)
        sys.exit(0)

    print(banner(args.ticker))
    print(f"Expiration: {target}   Underlying: {underlying}")
    print(f"\nCalls ({len(payload['calls'])}):")
    for c in payload["calls"][:15]:
        print(f"  K={c.get('strike'):<8} last={c.get('lastPrice')}  bid={c.get('bid')}  ask={c.get('ask')}  vol={c.get('volume')}  IV={c.get('impliedVolatility')}")
    print(f"\nPuts ({len(payload['puts'])}):")
    for p in payload["puts"][:15]:
        print(f"  K={p.get('strike'):<8} last={p.get('lastPrice')}  bid={p.get('bid')}  ask={p.get('ask')}  vol={p.get('volume')}  IV={p.get('impliedVolatility')}")


if __name__ == "__main__":
    main()
