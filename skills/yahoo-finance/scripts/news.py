#!/home/node/.openclaw-env/bin/python3
# SPDX-License-Identifier: MIT
"""
news.py — recent news headlines for a ticker.

Usage:
    python3 scripts/news.py AAPL
    python3 scripts/news.py NVDA --limit 20 --json

The yfinance news shape changed in 2024 — items now nest data under
`content`. This script normalizes both old and new shapes.
"""

import argparse
import sys
from datetime import datetime, timezone

from _yf import banner, emit_error_json, emit_json, get_ticker_obj, now_iso


def normalize_item(item: dict) -> dict:
    """Normalize a yfinance news item across old/new shapes."""
    # New shape: { id, content: { title, summary, pubDate, provider, canonicalUrl, ... } }
    content = item.get("content")
    if content and isinstance(content, dict):
        provider = content.get("provider") or {}
        canon = content.get("canonicalUrl") or {}
        click = content.get("clickThroughUrl") or {}
        return {
            "title": content.get("title"),
            "publisher": provider.get("displayName") if isinstance(provider, dict) else None,
            "link": canon.get("url") if isinstance(canon, dict) else (click.get("url") if isinstance(click, dict) else None),
            "published_at": content.get("pubDate") or content.get("displayTime"),
            "summary": content.get("summary"),
            "type": content.get("contentType"),
        }
    # Old shape: { title, publisher, link, providerPublishTime, ... }
    pub_time = item.get("providerPublishTime")
    iso_time = None
    if pub_time:
        try:
            iso_time = datetime.fromtimestamp(int(pub_time), tz=timezone.utc).isoformat()
        except (TypeError, ValueError):
            iso_time = None
    return {
        "title": item.get("title"),
        "publisher": item.get("publisher"),
        "link": item.get("link"),
        "published_at": iso_time,
        "summary": item.get("summary"),
        "type": item.get("type"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Recent news for a ticker.")
    parser.add_argument("ticker")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args()

    try:
        t = get_ticker_obj(args.ticker)
        raw = t.news or []
    except Exception as e:
        if args.as_json:
            emit_error_json(args.ticker, f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    items = [normalize_item(i) for i in raw[: args.limit]]

    if args.as_json:
        emit_json({"ticker": args.ticker, "fetched_at": now_iso(), "items": items})
        sys.exit(0)

    print(banner(args.ticker))
    if not items:
        print("(no news returned)")
        return
    for i, n in enumerate(items, 1):
        print(f"\n{i}. {n['title']}")
        print(f"   {n['publisher']}  ·  {n['published_at']}")
        if n.get("summary"):
            summary = n["summary"][:200] + ("..." if len(n["summary"]) > 200 else "")
            print(f"   {summary}")
        if n.get("link"):
            print(f"   {n['link']}")


if __name__ == "__main__":
    main()
