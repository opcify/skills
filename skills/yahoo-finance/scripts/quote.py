#!/home/node/.openclaw-env/bin/python3
# SPDX-License-Identifier: MIT
"""
quote.py — current quote(s) for one or more tickers.

Usage:
    python3 scripts/quote.py AAPL
    python3 scripts/quote.py AAPL MSFT GOOGL TSLA NVDA --json
    python3 scripts/quote.py BTC-USD ETH-USD ^GSPC EURUSD=X --json

Prefers fast_info (cheap, no network round-trip per field) and falls back
to info only for fields fast_info doesn't expose (currency, exchange,
market cap on some tickers). Designed to be batch-friendly: a failure on
one ticker does not abort the rest.

JSON output:
{
  "AAPL": {
    "price": 178.35,
    "previous_close": 176.55,
    "change": 1.80,
    "change_pct": 1.0195,
    "open": 177.10,
    "day_high": 179.00,
    "day_low": 176.80,
    "volume": 53412300,
    "market_cap": 2750000000000,
    "currency": "USD",
    "exchange": "NMS",
    "market_state": "REGULAR",
    "fetched_at": "2026-04-09T14:32:11+00:00"
  },
  ...
}
"""

import argparse
import sys

from _yf import (
    add_common_args,
    banner,
    emit_json,
    get_ticker_obj,
    now_iso,
    round_num,
    safe_num,
)


def fetch_quote(symbol: str) -> dict:
    """Fetch a single quote. Returns a dict with either fields or {error}."""
    try:
        t = get_ticker_obj(symbol)
        fi = None
        try:
            fi = t.fast_info
        except Exception:
            fi = None

        # fast_info exposes a dict-like interface; missing keys raise.
        def fi_get(key: str, default=None):
            if fi is None:
                return default
            try:
                return fi[key]
            except (KeyError, AttributeError, TypeError):
                try:
                    return getattr(fi, key)
                except AttributeError:
                    return default

        price = safe_num(fi_get("last_price")) or safe_num(fi_get("lastPrice"))
        prev = safe_num(fi_get("previous_close")) or safe_num(fi_get("previousClose"))
        open_ = safe_num(fi_get("open"))
        day_high = safe_num(fi_get("day_high")) or safe_num(fi_get("dayHigh"))
        day_low = safe_num(fi_get("day_low")) or safe_num(fi_get("dayLow"))
        volume = safe_num(fi_get("last_volume")) or safe_num(fi_get("lastVolume"))
        market_cap = safe_num(fi_get("market_cap")) or safe_num(fi_get("marketCap"))
        currency = fi_get("currency")
        exchange = fi_get("exchange")

        # Fall back to info only if fast_info missed the essentials
        if price is None or currency is None or market_cap is None:
            try:
                info = t.info or {}
                if price is None:
                    price = safe_num(
                        info.get("currentPrice")
                        or info.get("regularMarketPrice")
                        or info.get("previousClose")
                    )
                if prev is None:
                    prev = safe_num(info.get("regularMarketPreviousClose") or info.get("previousClose"))
                if open_ is None:
                    open_ = safe_num(info.get("regularMarketOpen") or info.get("open"))
                if day_high is None:
                    day_high = safe_num(info.get("regularMarketDayHigh") or info.get("dayHigh"))
                if day_low is None:
                    day_low = safe_num(info.get("regularMarketDayLow") or info.get("dayLow"))
                if volume is None:
                    volume = safe_num(info.get("regularMarketVolume") or info.get("volume"))
                if market_cap is None:
                    market_cap = safe_num(info.get("marketCap"))
                if currency is None:
                    currency = info.get("currency")
                if exchange is None:
                    exchange = info.get("exchange") or info.get("fullExchangeName")
                market_state = info.get("marketState")
            except Exception:
                market_state = None
        else:
            market_state = None

        change = None
        change_pct = None
        if price is not None and prev not in (None, 0):
            change = round(price - prev, 4)
            change_pct = round((price - prev) / prev * 100, 4)

        if price is None and market_cap is None:
            return {"error": f"No data returned for ticker '{symbol}'"}

        return {
            "price": round_num(price),
            "previous_close": round_num(prev),
            "change": change,
            "change_pct": change_pct,
            "open": round_num(open_),
            "day_high": round_num(day_high),
            "day_low": round_num(day_low),
            "volume": int(volume) if volume is not None else None,
            "market_cap": int(market_cap) if market_cap is not None else None,
            "currency": currency,
            "exchange": exchange,
            "market_state": market_state,
            "fetched_at": now_iso(),
        }
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def render_human(results: dict[str, dict]) -> str:
    lines = []
    for sym, q in results.items():
        if "error" in q:
            lines.append(f"{sym}: ERROR — {q['error']}")
            continue
        price = q.get("price")
        change = q.get("change")
        chg_pct = q.get("change_pct")
        cur = q.get("currency") or ""
        chg_str = ""
        if change is not None and chg_pct is not None:
            sign = "+" if change >= 0 else ""
            chg_str = f"  {sign}{change} ({sign}{chg_pct}%)"
        mc = q.get("market_cap")
        mc_str = f"  mcap={mc:,}" if mc else ""
        vol = q.get("volume")
        vol_str = f"  vol={vol:,}" if vol else ""
        lines.append(
            f"{sym}: {price} {cur}{chg_str}{vol_str}{mc_str}  [{q.get('exchange') or '?'}]"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch current quotes for one or more tickers from Yahoo Finance."
    )
    add_common_args(parser, multi=True)
    args = parser.parse_args()

    results: dict[str, dict] = {}
    for sym in args.tickers:
        sym_clean = sym.strip().upper() if not sym.startswith("^") else sym.strip()
        results[sym_clean] = fetch_quote(sym_clean)

    if args.as_json:
        emit_json(results)
        # Always exit 0 in JSON mode — errors are surfaced inside the payload
        sys.exit(0)
    else:
        print(banner(", ".join(results.keys())))
        print(render_human(results))
        # Exit non-zero in human mode if every ticker failed
        if all("error" in r for r in results.values()):
            sys.exit(1)


if __name__ == "__main__":
    main()
