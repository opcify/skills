#!/home/node/.openclaw-env/bin/python3
# SPDX-License-Identifier: MIT
"""
indicators.py — technical indicators computed from yfinance OHLCV.

Computes (in pure pandas/numpy, no TA-Lib dependency):
  - Trend:      SMA(9,21,50,200), EMA(9,21), golden/death cross flags
  - Momentum:   RSI(14), MACD(12,26,9), Stochastic(14,3), ADX(14)
  - Volatility: ATR(14), ATR%
  - Levels:     Fibonacci retracements (recent high/low), support/resistance
  - Summary:    BUY / HOLD / SELL with confidence in [0,1]

Usage:
    python3 scripts/indicators.py NVDA
    python3 scripts/indicators.py AAPL --period 6mo --interval 1d --json
    python3 scripts/indicators.py SPY --ma 9,21,50,200 --json
"""

import argparse
import sys

import numpy as np
import pandas as pd

from _yf import banner, emit_error_json, emit_json, get_ticker_obj, now_iso, round_num


# ---------------------------------------------------------------------------
# Indicator math (pure pandas — vectorized, no external TA libs)
# ---------------------------------------------------------------------------

def sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(window=n, min_periods=n).mean()


def ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14, d: int = 3):
    lowest_low = low.rolling(window=n, min_periods=n).min()
    highest_high = high.rolling(window=n, min_periods=n).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    return k, k.rolling(window=d, min_periods=d).mean()


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr


def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    return true_range(high, low, close).ewm(alpha=1 / n, min_periods=n, adjust=False).mean()


def adx(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move
    minus_dm = ((down_move > up_move) & (down_move > 0)) * down_move
    tr = true_range(high, low, close)
    atr_n = tr.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / n, min_periods=n, adjust=False).mean() / atr_n
    minus_di = 100 * minus_dm.ewm(alpha=1 / n, min_periods=n, adjust=False).mean() / atr_n
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()


def fib_levels(high: float, low: float) -> dict:
    if any(x is None or (isinstance(x, float) and np.isnan(x)) for x in (high, low)):
        return {}
    rng = high - low
    return {
        "0": round(high, 4),
        "23.6": round(high - rng * 0.236, 4),
        "38.2": round(high - rng * 0.382, 4),
        "50": round(high - rng * 0.500, 4),
        "61.8": round(high - rng * 0.618, 4),
        "78.6": round(high - rng * 0.786, 4),
        "100": round(low, 4),
    }


# ---------------------------------------------------------------------------
# Signal aggregation
# ---------------------------------------------------------------------------

def aggregate_signal(snapshot: dict) -> tuple[str, float]:
    """
    Combine indicator readings into a BUY/HOLD/SELL with confidence in [0,1].
    Heuristic, not a model — meant as a baseline the Technical Analyst can override.
    """
    score = 0.0
    weight = 0.0

    rsi_val = snapshot.get("momentum", {}).get("rsi14")
    if rsi_val is not None:
        weight += 1.0
        if rsi_val < 30:
            score += 1.0
        elif rsi_val > 70:
            score -= 1.0
        elif rsi_val > 55:
            score += 0.3
        elif rsi_val < 45:
            score -= 0.3

    macd_hist = snapshot.get("momentum", {}).get("macd", {}).get("hist")
    if macd_hist is not None:
        weight += 1.0
        score += 0.6 if macd_hist > 0 else -0.6

    trend = snapshot.get("trend", {})
    if trend.get("golden_cross"):
        weight += 1.0
        score += 1.0
    if trend.get("death_cross"):
        weight += 1.0
        score -= 1.0

    sma50 = trend.get("sma", {}).get("50")
    sma200 = trend.get("sma", {}).get("200")
    price = snapshot.get("price")
    if price is not None and sma50 is not None and sma200 is not None:
        weight += 1.0
        if price > sma50 > sma200:
            score += 0.8
        elif price < sma50 < sma200:
            score -= 0.8

    adx_val = snapshot.get("momentum", {}).get("adx14")
    # ADX > 25 means trend is real — amplify whichever side we're on
    if adx_val is not None and adx_val > 25 and weight > 0:
        score *= 1.15

    if weight == 0:
        return "HOLD", 0.0

    normalized = max(-1.0, min(1.0, score / weight))
    if normalized > 0.35:
        return "BUY", round(min(1.0, abs(normalized)), 3)
    if normalized < -0.35:
        return "SELL", round(min(1.0, abs(normalized)), 3)
    return "HOLD", round(abs(normalized), 3)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def compute(symbol: str, period: str, interval: str, ma_periods: list[int]) -> dict:
    t = get_ticker_obj(symbol)
    df = t.history(period=period, interval=interval, auto_adjust=False)
    if df is None or df.empty:
        raise ValueError(f"Empty history for {symbol}")

    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    # SMAs requested + the canonical 9/21/50/200 set used for cross detection
    sma_set = sorted(set(ma_periods + [9, 21, 50, 200]))
    sma_vals = {str(n): round_num(sma(close, n).iloc[-1]) for n in sma_set if len(close) >= n}
    ema_vals = {
        "9": round_num(ema(close, 9).iloc[-1]) if len(close) >= 9 else None,
        "21": round_num(ema(close, 21).iloc[-1]) if len(close) >= 21 else None,
    }

    # Cross detection: was 50 below 200 yesterday and above today?
    golden = death = False
    if len(close) >= 200:
        s50 = sma(close, 50)
        s200 = sma(close, 200)
        if s50.iloc[-2] is not None and s200.iloc[-2] is not None:
            golden = bool(s50.iloc[-2] <= s200.iloc[-2] and s50.iloc[-1] > s200.iloc[-1])
            death = bool(s50.iloc[-2] >= s200.iloc[-2] and s50.iloc[-1] < s200.iloc[-1])

    rsi_val = round_num(rsi(close, 14).iloc[-1]) if len(close) >= 15 else None
    macd_line, sig_line, hist = macd(close)
    macd_block = {
        "line": round_num(macd_line.iloc[-1]) if len(close) >= 26 else None,
        "signal": round_num(sig_line.iloc[-1]) if len(close) >= 35 else None,
        "hist": round_num(hist.iloc[-1]) if len(close) >= 35 else None,
    }
    k, d = stochastic(high, low, close)
    stoch_block = {
        "k": round_num(k.iloc[-1]) if len(close) >= 14 else None,
        "d": round_num(d.iloc[-1]) if len(close) >= 17 else None,
    }
    adx_val = round_num(adx(high, low, close).iloc[-1]) if len(close) >= 28 else None
    atr_val = atr(high, low, close).iloc[-1] if len(close) >= 15 else None
    last_close = float(close.iloc[-1])
    atr_pct = round((atr_val / last_close * 100), 4) if atr_val is not None and not np.isnan(atr_val) and last_close else None

    lookback = min(60, len(df))
    recent = df.tail(lookback)
    recent_high = float(recent["High"].max())
    recent_low = float(recent["Low"].min())

    snapshot = {
        "ticker": symbol,
        "period": period,
        "interval": interval,
        "price": round(last_close, 4),
        "fetched_at": now_iso(),
        "trend": {
            "sma": sma_vals,
            "ema": ema_vals,
            "golden_cross": golden,
            "death_cross": death,
            "above_200dma": last_close > sma_vals.get("200", float("inf")) if sma_vals.get("200") is not None else None,
        },
        "momentum": {
            "rsi14": rsi_val,
            "macd": macd_block,
            "stochastic": stoch_block,
            "adx14": adx_val,
        },
        "volatility": {
            "atr14": round_num(atr_val) if atr_val is not None else None,
            "atr_pct": atr_pct,
        },
        "levels": {
            "recent_high": round(recent_high, 4),
            "recent_low": round(recent_low, 4),
            "fib": fib_levels(recent_high, recent_low),
        },
    }
    sig, conf = aggregate_signal(snapshot)
    snapshot["signal_summary"] = sig
    snapshot["confidence"] = conf
    return snapshot


def render_human(s: dict) -> str:
    L = [banner(s["ticker"])]
    L.append(f"Price: {s['price']}   Signal: {s['signal_summary']}  conf={s['confidence']}")
    t = s["trend"]
    L.append(f"\nTrend:")
    L.append(f"  SMA: {t['sma']}")
    L.append(f"  EMA: {t['ema']}")
    L.append(f"  Golden cross: {t['golden_cross']}   Death cross: {t['death_cross']}   Above 200DMA: {t['above_200dma']}")
    m = s["momentum"]
    L.append(f"\nMomentum:")
    L.append(f"  RSI(14):    {m['rsi14']}")
    L.append(f"  MACD:       line={m['macd']['line']}  signal={m['macd']['signal']}  hist={m['macd']['hist']}")
    L.append(f"  Stoch:      %K={m['stochastic']['k']}  %D={m['stochastic']['d']}")
    L.append(f"  ADX(14):    {m['adx14']}")
    v = s["volatility"]
    L.append(f"\nVolatility:")
    L.append(f"  ATR(14):    {v['atr14']}    ATR%: {v['atr_pct']}")
    lv = s["levels"]
    L.append(f"\nLevels:")
    L.append(f"  Recent range: {lv['recent_low']} → {lv['recent_high']}")
    L.append(f"  Fib retracements: {lv['fib']}")
    return "\n".join(L)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute technical indicators for a ticker."
    )
    parser.add_argument("ticker")
    parser.add_argument("--period", default="6mo")
    parser.add_argument("--interval", default="1d")
    parser.add_argument(
        "--ma",
        default="9,21,50,200",
        help="Comma-separated SMA periods (default 9,21,50,200)",
    )
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args()

    try:
        ma_periods = [int(x.strip()) for x in args.ma.split(",") if x.strip()]
    except ValueError:
        print("ERROR: --ma must be comma-separated integers", file=sys.stderr)
        sys.exit(1)

    try:
        result = compute(args.ticker, args.period, args.interval, ma_periods)
    except Exception as e:
        if args.as_json:
            emit_error_json(args.ticker, f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if args.as_json:
        emit_json(result)
    else:
        print(render_human(result))


if __name__ == "__main__":
    main()
