#!/home/node/.openclaw-env/bin/python3
# SPDX-License-Identifier: MIT
"""
search.py — search Yahoo Finance for tickers by name or partial symbol.

Usage:
    python3 scripts/search.py "apple"
    python3 scripts/search.py "tesla" --json
    python3 scripts/search.py "NVIDIA" --json
"""

import argparse
import sys

from _yf import emit_error_json, emit_json, now_iso


def main() -> None:
    parser = argparse.ArgumentParser(description="Search Yahoo Finance tickers.")
    parser.add_argument("query", help="Search query (company name or partial symbol)")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args()

    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance not installed. Run: pip install yfinance", file=sys.stderr)
        sys.exit(1)

    try:
        # yfinance.Search exists in 0.2.40+; fall back to a Lookup if not
        if hasattr(yf, "Search"):
            s = yf.Search(args.query, max_results=args.limit)
            quotes = s.quotes or []
        else:
            quotes = []
    except Exception as e:
        if args.as_json:
            emit_error_json(args.query, f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    results = []
    for q in quotes[: args.limit]:
        results.append(
            {
                "symbol": q.get("symbol"),
                "name": q.get("shortname") or q.get("longname"),
                "exchange": q.get("exchange") or q.get("exchDisp"),
                "type": q.get("quoteType") or q.get("typeDisp"),
                "score": q.get("score"),
            }
        )

    if args.as_json:
        emit_json({"query": args.query, "results": results, "fetched_at": now_iso()})
        sys.exit(0)

    print(f"Search: {args.query}    ({len(results)} results)")
    for r in results:
        print(f"  {r['symbol']:<10} {r['type'] or '':<10} {r['exchange'] or '':<10} {r['name'] or ''}")


if __name__ == "__main__":
    main()
