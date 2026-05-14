#!/home/node/.openclaw-env/bin/python3
# SPDX-License-Identifier: MIT
"""
analyst.py — analyst price targets, recommendations, upgrades/downgrades.

Usage:
    python3 scripts/analyst.py AAPL
    python3 scripts/analyst.py NVDA --json
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyst recommendations and price targets."
    )
    parser.add_argument("ticker")
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args()

    try:
        t = get_ticker_obj(args.ticker)
        info = t.info or {}
    except Exception as e:
        if args.as_json:
            emit_error_json(args.ticker, f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Price targets — yfinance exposes via info AND analyst_price_targets
    targets_obj = safe_attr(t, "analyst_price_targets")
    if isinstance(targets_obj, dict):
        targets = {k: round_num(v) for k, v in targets_obj.items()}
    else:
        targets = {
            "current": round_num(info.get("currentPrice")),
            "low": round_num(info.get("targetLowPrice")),
            "mean": round_num(info.get("targetMeanPrice")),
            "median": round_num(info.get("targetMedianPrice")),
            "high": round_num(info.get("targetHighPrice")),
        }

    # Recommendations summary — most recent row from .recommendations or .recommendations_summary
    rec_summary = None
    rec_df = safe_attr(t, "recommendations")
    if rec_df is not None and not getattr(rec_df, "empty", True):
        try:
            last_row = rec_df.iloc[0] if "period" in rec_df.columns else rec_df.iloc[-1]
            rec_summary = {
                "strong_buy": int(safe_num(last_row.get("strongBuy")) or 0),
                "buy": int(safe_num(last_row.get("buy")) or 0),
                "hold": int(safe_num(last_row.get("hold")) or 0),
                "sell": int(safe_num(last_row.get("sell")) or 0),
                "strong_sell": int(safe_num(last_row.get("strongSell")) or 0),
            }
        except Exception:
            rec_summary = None

    if rec_summary is None:
        rec_summary = {
            "strong_buy": 0,
            "buy": 0,
            "hold": 0,
            "sell": 0,
            "strong_sell": 0,
        }

    rec_summary["mean_rating"] = round_num(info.get("recommendationMean"))
    rec_summary["recommendation_key"] = info.get("recommendationKey")
    rec_summary["analyst_count"] = info.get("numberOfAnalystOpinions")

    # Upgrades / downgrades
    ud_df = safe_attr(t, "upgrades_downgrades")
    upgrades_downgrades = []
    if ud_df is not None and not getattr(ud_df, "empty", True):
        upgrades_downgrades = df_to_records(ud_df)[:20]

    payload = {
        "ticker": args.ticker,
        "price_target": targets,
        "recommendation": rec_summary,
        "upgrades_downgrades": upgrades_downgrades,
        "fetched_at": now_iso(),
    }

    if args.as_json:
        emit_json(payload)
        sys.exit(0)

    print(banner(args.ticker))
    print(f"Price targets: {targets}")
    print(f"\nRecommendation: {rec_summary}")
    if upgrades_downgrades:
        print(f"\nRecent actions ({len(upgrades_downgrades)}):")
        for r in upgrades_downgrades[:10]:
            print(f"  {r}")


if __name__ == "__main__":
    main()
