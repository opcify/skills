#!/home/node/.openclaw-env/bin/python3
# SPDX-License-Identifier: MIT
"""
volatility.py — historical volatility, ATR, drawdown, and beta vs SPY.

Designed for the Risk Manager: ATR drives stop-loss distance, realized
volatility informs position sizing, beta-vs-SPY contextualizes systemic risk.

Usage:
    python3 scripts/volatility.py AAPL
    python3 scripts/volatility.py NVDA --lookback 90 --json
"""

import argparse
import math
import sys

import numpy as np
import pandas as pd

from _yf import banner, emit_error_json, emit_json, get_ticker_obj, now_iso, round_num


TRADING_DAYS = 252


def realized_vol(close: pd.Series, window: int) -> float | None:
    """Annualized realized volatility from log returns."""
    if len(close) < window + 1:
        return None
    returns = np.log(close / close.shift(1)).dropna()
    if len(returns) < window:
        return None
    sample = returns.tail(window)
    return float(sample.std() * math.sqrt(TRADING_DAYS))


def downside_dev(close: pd.Series, window: int) -> float | None:
    if len(close) < window + 1:
        return None
    returns = np.log(close / close.shift(1)).dropna().tail(window)
    neg = returns[returns < 0]
    if len(neg) == 0:
        return 0.0
    return float(neg.std() * math.sqrt(TRADING_DAYS))


def max_drawdown(close: pd.Series) -> float | None:
    if len(close) < 2:
        return None
    running_max = close.cummax()
    dd = (close / running_max - 1.0)
    return float(dd.min())


def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> float | None:
    if len(close) < n + 1:
        return None
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return float(tr.ewm(alpha=1 / n, min_periods=n, adjust=False).mean().iloc[-1])


def beta_vs_spy(symbol: str, lookback_days: int) -> float | None:
    """Compute beta against SPY over the lookback window."""
    try:
        import yfinance as yf
        # Add a buffer so we have enough returns
        period = "2y" if lookback_days > 252 else "1y"
        data = yf.download(
            [symbol, "SPY"],
            period=period,
            interval="1d",
            progress=False,
            auto_adjust=False,
        )
        if data is None or data.empty:
            return None
        closes = data["Close"]
        if symbol not in closes.columns or "SPY" not in closes.columns:
            return None
        rets = np.log(closes / closes.shift(1)).dropna().tail(lookback_days)
        if len(rets) < 20:
            return None
        cov = rets.cov().loc[symbol, "SPY"]
        var_spy = rets["SPY"].var()
        if var_spy == 0:
            return None
        return float(cov / var_spy)
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Historical volatility, ATR, drawdown, beta.")
    parser.add_argument("ticker")
    parser.add_argument(
        "--lookback",
        type=int,
        default=60,
        help="Lookback window in trading days for realized vol (default 60)",
    )
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args()

    try:
        t = get_ticker_obj(args.ticker)
        df = t.history(period="2y", interval="1d", auto_adjust=False)
    except Exception as e:
        if args.as_json:
            emit_error_json(args.ticker, f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if df is None or df.empty:
        if args.as_json:
            emit_error_json(args.ticker, "Empty history")
            sys.exit(0)
        print(f"ERROR: empty history for {args.ticker}", file=sys.stderr)
        sys.exit(1)

    close = df["Close"].dropna()
    high = df["High"]
    low = df["Low"]
    last_price = float(close.iloc[-1])

    hv30 = realized_vol(close, 30)
    hv60 = realized_vol(close, 60)
    hv_lookback = realized_vol(close, args.lookback)
    dd_dev = downside_dev(close, args.lookback)
    mdd = max_drawdown(close)
    atr14 = atr(high, low, close, 14)
    atr_pct = (atr14 / last_price * 100) if atr14 and last_price else None

    payload = {
        "ticker": args.ticker,
        "last_price": round(last_price, 4),
        "lookback_days": args.lookback,
        "realized_vol_annualized": round_num(hv_lookback),
        "hv30": round_num(hv30),
        "hv60": round_num(hv60),
        "atr14": round_num(atr14),
        "atr14_pct": round_num(atr_pct),
        "downside_dev": round_num(dd_dev),
        "max_drawdown_pct": round_num(mdd * 100 if mdd is not None else None),
        "beta_vs_spy": round_num(beta_vs_spy(args.ticker, args.lookback)),
        "fetched_at": now_iso(),
    }

    if args.as_json:
        emit_json(payload)
        sys.exit(0)

    print(banner(args.ticker))
    print(f"Last price:           {payload['last_price']}")
    print(f"Realized vol ({args.lookback}d): {payload['realized_vol_annualized']}")
    print(f"HV(30):               {payload['hv30']}")
    print(f"HV(60):               {payload['hv60']}")
    print(f"ATR(14):              {payload['atr14']}     ATR%: {payload['atr14_pct']}")
    print(f"Downside dev:         {payload['downside_dev']}")
    print(f"Max drawdown:         {payload['max_drawdown_pct']}%")
    print(f"Beta vs SPY:          {payload['beta_vs_spy']}")
    print()
    print("Risk sizing hints:")
    if payload["atr14"]:
        print(f"  Suggested stop distance: 1.5×ATR = {round(payload['atr14'] * 1.5, 4)}")
        print(f"  Suggested stop distance: 2.0×ATR = {round(payload['atr14'] * 2.0, 4)}")


if __name__ == "__main__":
    main()
