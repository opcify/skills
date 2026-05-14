#!/home/node/.openclaw-env/bin/python3
# SPDX-License-Identifier: MIT
"""
earnings.py — earnings dates, EPS estimates, revisions, and growth projections.

Usage:
    python3 scripts/earnings.py AAPL
    python3 scripts/earnings.py NVDA --json
"""

import argparse
import sys
from datetime import datetime, timezone

from _yf import (
    banner,
    df_to_columnar,
    df_to_records,
    emit_error_json,
    emit_json,
    get_ticker_obj,
    now_iso,
)


def safe_attr(t, name):
    try:
        return getattr(t, name)
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Earnings dates and estimates.")
    parser.add_argument("ticker")
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args()

    try:
        t = get_ticker_obj(args.ticker)
    except Exception as e:
        if args.as_json:
            emit_error_json(args.ticker, f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    payload = {"ticker": args.ticker, "fetched_at": now_iso()}

    # Earnings dates (next + recent)
    edates_df = safe_attr(t, "earnings_dates")
    next_date = None
    earnings_history = []
    if edates_df is not None and not edates_df.empty:
        records = df_to_records(edates_df)
        earnings_history = records[:20]
        # Find the next future date
        now_utc = datetime.now(timezone.utc).isoformat()
        future = [r for r in records if (r.get("date") or "") > now_utc]
        if future:
            next_date = sorted(future, key=lambda r: r["date"])[0]["date"]
    payload["next_earnings_date"] = next_date
    payload["earnings_history"] = earnings_history

    # EPS estimates
    eps_est = safe_attr(t, "earnings_estimate")
    payload["eps_estimate"] = df_to_columnar(eps_est) if eps_est is not None and not getattr(eps_est, "empty", True) else None

    rev_est = safe_attr(t, "revenue_estimate")
    payload["revenue_estimate"] = df_to_columnar(rev_est) if rev_est is not None and not getattr(rev_est, "empty", True) else None

    eps_trend = safe_attr(t, "eps_trend")
    payload["eps_trend"] = df_to_columnar(eps_trend) if eps_trend is not None and not getattr(eps_trend, "empty", True) else None

    eps_rev = safe_attr(t, "eps_revisions")
    payload["eps_revisions"] = df_to_columnar(eps_rev) if eps_rev is not None and not getattr(eps_rev, "empty", True) else None

    growth = safe_attr(t, "growth_estimates")
    payload["growth_estimates"] = df_to_columnar(growth) if growth is not None and not getattr(growth, "empty", True) else None

    if args.as_json:
        emit_json(payload)
        sys.exit(0)

    print(banner(args.ticker))
    print(f"Next earnings: {payload['next_earnings_date'] or 'N/A'}")
    print()
    if earnings_history:
        print("Recent earnings (most recent first):")
        for row in earnings_history[:5]:
            d = row.get("date", "?")
            est = row.get("EPS Estimate") or row.get("epsEstimate")
            act = row.get("Reported EPS") or row.get("epsActual")
            surp = row.get("Surprise(%)") or row.get("surprise")
            print(f"  {d}  est={est}  actual={act}  surprise={surp}")
    if payload.get("eps_revisions"):
        print(f"\nEPS revisions: {payload['eps_revisions']}")
    if payload.get("growth_estimates"):
        print(f"\nGrowth estimates: {payload['growth_estimates']}")


if __name__ == "__main__":
    main()
