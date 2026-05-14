#!/home/node/.openclaw-env/bin/python3
# SPDX-License-Identifier: MIT
"""
financials.py — income statement / balance sheet / cash flow.

Usage:
    python3 scripts/financials.py AAPL --statement income --period annual
    python3 scripts/financials.py MSFT --statement balance --period quarterly --json
    python3 scripts/financials.py NVDA --statement cashflow --period ttm --json

Statements: income | balance | cashflow
Periods:    annual | quarterly | ttm

JSON output:
{
  "ticker": "AAPL",
  "statement": "income",
  "period": "annual",
  "columns": ["2024-09-28T00:00:00", "2023-09-30T00:00:00", ...],
  "rows": { "Total Revenue": [394328000000, 383285000000, ...], ... }
}
"""

import argparse
import sys

from _yf import banner, df_to_columnar, emit_error_json, emit_json, get_ticker_obj, now_iso


STATEMENT_MAP = {
    ("income", "annual"): "income_stmt",
    ("income", "quarterly"): "quarterly_income_stmt",
    ("income", "ttm"): "ttm_income_stmt",
    ("balance", "annual"): "balance_sheet",
    ("balance", "quarterly"): "quarterly_balance_sheet",
    ("balance", "ttm"): None,  # not supported by yfinance
    ("cashflow", "annual"): "cashflow",
    ("cashflow", "quarterly"): "quarterly_cashflow",
    ("cashflow", "ttm"): "ttm_cashflow",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch financial statements.")
    parser.add_argument("ticker")
    parser.add_argument(
        "--statement",
        choices=["income", "balance", "cashflow"],
        default="income",
    )
    parser.add_argument(
        "--period", choices=["annual", "quarterly", "ttm"], default="annual"
    )
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args()

    attr = STATEMENT_MAP.get((args.statement, args.period))
    if attr is None:
        msg = f"{args.statement} statement does not support period={args.period}"
        if args.as_json:
            emit_error_json(args.ticker, msg)
            sys.exit(0)
        print(f"ERROR: {msg}", file=sys.stderr)
        sys.exit(1)

    try:
        t = get_ticker_obj(args.ticker)
        df = getattr(t, attr)
    except Exception as e:
        if args.as_json:
            emit_error_json(args.ticker, f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if df is None or df.empty:
        if args.as_json:
            emit_error_json(args.ticker, "No financial data available")
            sys.exit(0)
        print(f"ERROR: no financial data for {args.ticker}", file=sys.stderr)
        sys.exit(1)

    if args.as_json:
        payload = {
            "ticker": args.ticker,
            "statement": args.statement,
            "period": args.period,
            "fetched_at": now_iso(),
            **df_to_columnar(df),
        }
        emit_json(payload)
        sys.exit(0)

    print(banner(args.ticker))
    print(f"Statement: {args.statement}  ·  Period: {args.period}")
    print()
    print(df.round(2).to_string())


if __name__ == "__main__":
    main()
