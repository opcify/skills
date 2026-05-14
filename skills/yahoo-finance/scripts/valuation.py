#!/home/node/.openclaw-env/bin/python3
# SPDX-License-Identifier: MIT
"""
valuation.py — valuation multiples and key ratios from Ticker.info.

Usage:
    python3 scripts/valuation.py AAPL
    python3 scripts/valuation.py MSFT --json

Pulls market cap, enterprise value, P/E (trailing & forward), P/S, PEG,
EV/EBITDA, margins, beta, dividend yield, 52-week range.
"""

import argparse
import sys

from _yf import banner, emit_error_json, emit_json, get_ticker_obj, now_iso, round_num, safe_num


def main() -> None:
    parser = argparse.ArgumentParser(description="Valuation multiples and key ratios.")
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

    if not info:
        if args.as_json:
            emit_error_json(args.ticker, "No info available")
            sys.exit(0)
        print(f"ERROR: no info for {args.ticker}", file=sys.stderr)
        sys.exit(1)

    price = safe_num(info.get("currentPrice") or info.get("regularMarketPrice"))
    fifty_two_high = safe_num(info.get("fiftyTwoWeekHigh"))
    fifty_two_low = safe_num(info.get("fiftyTwoWeekLow"))
    pct_off_high = None
    if price and fifty_two_high:
        pct_off_high = round((price / fifty_two_high - 1) * 100, 2)

    payload = {
        "ticker": args.ticker,
        "company": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "currency": info.get("currency"),
        "price": round_num(price),
        "market_cap": safe_num(info.get("marketCap")),
        "enterprise_value": safe_num(info.get("enterpriseValue")),
        "pe_trailing": round_num(info.get("trailingPE")),
        "pe_forward": round_num(info.get("forwardPE")),
        "ps_trailing": round_num(info.get("priceToSalesTrailing12Months")),
        "pb": round_num(info.get("priceToBook")),
        "peg": round_num(info.get("pegRatio") or info.get("trailingPegRatio")),
        "ev_ebitda": round_num(info.get("enterpriseToEbitda")),
        "ev_revenue": round_num(info.get("enterpriseToRevenue")),
        "gross_margin": round_num(info.get("grossMargins")),
        "operating_margin": round_num(info.get("operatingMargins")),
        "profit_margin": round_num(info.get("profitMargins")),
        "ebitda_margin": round_num(info.get("ebitdaMargins")),
        "return_on_equity": round_num(info.get("returnOnEquity")),
        "return_on_assets": round_num(info.get("returnOnAssets")),
        "debt_to_equity": round_num(info.get("debtToEquity")),
        "current_ratio": round_num(info.get("currentRatio")),
        "quick_ratio": round_num(info.get("quickRatio")),
        "free_cashflow": safe_num(info.get("freeCashflow")),
        "operating_cashflow": safe_num(info.get("operatingCashflow")),
        "revenue_growth": round_num(info.get("revenueGrowth")),
        "earnings_growth": round_num(info.get("earningsGrowth")),
        "beta": round_num(info.get("beta")),
        "dividend_yield": round_num(info.get("dividendYield")),
        "payout_ratio": round_num(info.get("payoutRatio")),
        "fifty_two_week": {
            "high": round_num(fifty_two_high),
            "low": round_num(fifty_two_low),
            "pct_off_high": pct_off_high,
        },
        "shares_outstanding": safe_num(info.get("sharesOutstanding")),
        "float_shares": safe_num(info.get("floatShares")),
        "short_ratio": round_num(info.get("shortRatio")),
        "fetched_at": now_iso(),
    }

    if args.as_json:
        emit_json(payload)
        sys.exit(0)

    print(banner(args.ticker))
    print(f"{payload['company']}  [{payload['sector']} / {payload['industry']}]")
    print()
    print(f"Price:       {payload['price']} {payload['currency']}")
    print(f"Market cap:  {payload['market_cap']:,}" if payload["market_cap"] else "Market cap:  N/A")
    print(f"EV:          {payload['enterprise_value']:,}" if payload["enterprise_value"] else "EV:          N/A")
    print()
    print("Valuation multiples:")
    print(f"  P/E trailing:   {payload['pe_trailing']}")
    print(f"  P/E forward:    {payload['pe_forward']}")
    print(f"  P/S:            {payload['ps_trailing']}")
    print(f"  P/B:            {payload['pb']}")
    print(f"  PEG:            {payload['peg']}")
    print(f"  EV/EBITDA:      {payload['ev_ebitda']}")
    print()
    print("Margins & returns:")
    print(f"  Gross margin:   {payload['gross_margin']}")
    print(f"  Op margin:      {payload['operating_margin']}")
    print(f"  Net margin:     {payload['profit_margin']}")
    print(f"  ROE:            {payload['return_on_equity']}")
    print(f"  ROA:            {payload['return_on_assets']}")
    print()
    print(f"Beta:           {payload['beta']}")
    print(f"Dividend yield: {payload['dividend_yield']}")
    print(f"52w range:      {payload['fifty_two_week']['low']} → {payload['fifty_two_week']['high']}  ({payload['fifty_two_week']['pct_off_high']}% from high)")


if __name__ == "__main__":
    main()
