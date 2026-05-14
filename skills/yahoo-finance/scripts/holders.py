#!/home/node/.openclaw-env/bin/python3
# SPDX-License-Identifier: MIT
"""
holders.py — major / institutional / mutual fund holders + insider activity.

Usage:
    python3 scripts/holders.py AAPL
    python3 scripts/holders.py NVDA --json
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
    safe_num,
)


def safe_attr(t, name):
    try:
        return getattr(t, name)
    except Exception:
        return None


def parse_major(df) -> dict:
    """The major_holders DataFrame is a 2-column key/value table on most tickers."""
    out = {}
    if df is None or getattr(df, "empty", True):
        return out
    try:
        # Newer yfinance returns a Series-like with index labels
        if hasattr(df, "to_dict"):
            d = df.to_dict() if hasattr(df, "to_dict") else {}
            # Older shape: 2 columns, label in col[1]
            if isinstance(d, dict) and len(d) > 0:
                first_key = next(iter(d))
                inner = d[first_key]
                if isinstance(inner, dict):
                    for k, v in inner.items():
                        out[str(k)] = v
                    return out
        for _, row in df.iterrows():
            try:
                vals = list(row.values)
                if len(vals) >= 2:
                    out[str(vals[1])] = vals[0]
            except Exception:
                continue
    except Exception:
        pass
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Holders and insider activity.")
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

    payload["major"] = parse_major(safe_attr(t, "major_holders"))

    inst_df = safe_attr(t, "institutional_holders")
    payload["top_institutions"] = (
        df_to_records(inst_df)[:15] if inst_df is not None and not getattr(inst_df, "empty", True) else []
    )

    mf_df = safe_attr(t, "mutualfund_holders")
    payload["top_mutual_funds"] = (
        df_to_records(mf_df)[:15] if mf_df is not None and not getattr(mf_df, "empty", True) else []
    )

    ins_pur = safe_attr(t, "insider_purchases")
    if ins_pur is not None and not getattr(ins_pur, "empty", True):
        payload["insider_purchases_summary"] = df_to_records(ins_pur)
    else:
        payload["insider_purchases_summary"] = []

    ins_tx = safe_attr(t, "insider_transactions")
    payload["recent_insider_transactions"] = (
        df_to_records(ins_tx)[:25] if ins_tx is not None and not getattr(ins_tx, "empty", True) else []
    )

    if args.as_json:
        emit_json(payload)
        sys.exit(0)

    print(banner(args.ticker))
    print(f"Major holders: {payload['major']}")
    print(f"\nTop institutions ({len(payload['top_institutions'])}):")
    for h in payload["top_institutions"][:10]:
        print(f"  {h}")
    print(f"\nRecent insider transactions ({len(payload['recent_insider_transactions'])}):")
    for tx in payload["recent_insider_transactions"][:10]:
        print(f"  {tx}")


if __name__ == "__main__":
    main()
