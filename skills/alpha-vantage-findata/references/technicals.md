# Technical Analysis

**Goal:** Read trend, momentum, volatility, and volume signals to time entries and exits.

## The one-call pattern (always start here)

Calling each indicator endpoint separately costs 1 quota slot per indicator per ticker. An 8-indicator dump on 5 tickers = 40 calls — impossible on the 25/day free tier. **Pull the OHLCV history once and compute everything locally:**

```bash
marketdata-cli time_series_daily_adjusted AAPL -o full
```

That's 1 quota slot. Feed the `Time Series (Daily)` block into `code-exec` and compute every indicator below from the same bar series. Use the **adjusted** series — the unadjusted one doesn't back-correct splits and dividends and will produce misleading SMA / RSI / drawdown values across split events.

## Per-indicator endpoints (when you really need just one)

If you only need a single indicator and want Alpha Vantage's reference implementation, hit the dedicated endpoint. All take a `SYMBOL` positional and the common flags `-i/--interval`, `--time_period`, and `--series_type`. Run `marketdata-cli <indicator> --help` for endpoint-specific flags.

### Moving averages

```bash
marketdata-cli sma   AAPL -i daily --time_period 50  --series_type close
marketdata-cli ema   AAPL -i daily --time_period 21  --series_type close
marketdata-cli wma   AAPL -i daily --time_period 20  --series_type close   # weighted
marketdata-cli dema  AAPL -i daily --time_period 20  --series_type close   # double-exp
marketdata-cli tema  AAPL -i daily --time_period 20  --series_type close   # triple-exp
marketdata-cli trima AAPL -i daily --time_period 20  --series_type close   # triangular
marketdata-cli kama  AAPL -i daily --time_period 20  --series_type close   # Kaufman adaptive
marketdata-cli mama  AAPL -i daily --series_type close                     # MESA adaptive
marketdata-cli t3    AAPL -i daily --time_period 20  --series_type close   # T3
```

### Momentum oscillators

```bash
marketdata-cli rsi      AAPL -i daily --time_period 14 --series_type close
marketdata-cli stoch    AAPL -i daily
marketdata-cli stochf   AAPL -i daily                                        # fast stochastic
marketdata-cli stochrsi AAPL -i daily --time_period 14 --series_type close   # stochastic RSI
marketdata-cli willr    AAPL -i daily --time_period 14                       # Williams %R
marketdata-cli cci      AAPL -i daily --time_period 20                       # commodity channel index
marketdata-cli cmo      AAPL -i daily --time_period 14 --series_type close   # Chande momentum
marketdata-cli mom      AAPL -i daily --time_period 10 --series_type close   # raw momentum
marketdata-cli roc      AAPL -i daily --time_period 10 --series_type close   # rate of change
marketdata-cli rocr     AAPL -i daily --time_period 10 --series_type close   # rate of change ratio
marketdata-cli mfi      AAPL -i daily --time_period 14                       # money flow index
marketdata-cli ultosc   AAPL -i daily                                        # ultimate oscillator
marketdata-cli bop      AAPL -i daily                                        # balance of power
```

### MACD family

```bash
marketdata-cli macd    AAPL -i daily --series_type close
marketdata-cli macdext AAPL -i daily --series_type close   # MACD with custom MA types
marketdata-cli ppo     AAPL -i daily --series_type close   # percentage price oscillator
marketdata-cli apo     AAPL -i daily --series_type close   # absolute price oscillator
```

### Trend strength / DMI

```bash
marketdata-cli adx      AAPL -i daily --time_period 14   # average directional index
marketdata-cli adxr     AAPL -i daily --time_period 14   # ADX rating
marketdata-cli dx       AAPL -i daily --time_period 14   # directional movement index
marketdata-cli plus_di  AAPL -i daily --time_period 14
marketdata-cli minus_di AAPL -i daily --time_period 14
marketdata-cli plus_dm  AAPL -i daily --time_period 14
marketdata-cli minus_dm AAPL -i daily --time_period 14
marketdata-cli aroon    AAPL -i daily --time_period 25
marketdata-cli aroonosc AAPL -i daily --time_period 25
marketdata-cli trix     AAPL -i daily --time_period 30 --series_type close
marketdata-cli sar      AAPL -i daily                    # parabolic SAR
```

### Volatility

```bash
marketdata-cli atr      AAPL -i daily --time_period 14
marketdata-cli natr     AAPL -i daily --time_period 14   # normalized ATR
marketdata-cli trange   AAPL -i daily                    # true range
marketdata-cli bbands   AAPL -i daily --time_period 20 --series_type close
marketdata-cli midpoint AAPL -i daily --time_period 14 --series_type close
marketdata-cli midprice AAPL -i daily --time_period 14
```

### Volume

```bash
marketdata-cli obv   AAPL -i daily                   # on-balance volume
marketdata-cli vwap  AAPL -i 15min                   # volume-weighted average price (intraday only)
marketdata-cli ad    AAPL -i daily                   # Chaikin A/D line
marketdata-cli adosc AAPL -i daily                   # Chaikin A/D oscillator
```

### Hilbert transform (cycle / regime detection)

```bash
marketdata-cli ht_trendline AAPL -i daily --series_type close
marketdata-cli ht_sine      AAPL -i daily --series_type close
marketdata-cli ht_trendmode AAPL -i daily --series_type close   # 0/1 trend vs cycle flag
marketdata-cli ht_dcperiod  AAPL -i daily --series_type close
marketdata-cli ht_dcphase   AAPL -i daily --series_type close
marketdata-cli ht_phasor    AAPL -i daily --series_type close
```

## Multi-timeframe analysis

```bash
# Daily structure (1 call)
marketdata-cli time_series_daily_adjusted NVDA -o full

# Hourly structure (1 call)
marketdata-cli time_series_intraday NVDA -i 60min -o full --extended_hours
```

Two calls cover the full multi-timeframe view. Compute indicators on both bar series in `code-exec` and look for confirmation across timeframes.

## Quota-aware checklist

Before calling any indicator endpoint individually:

1. Could `time_series_daily_adjusted` + local computation answer the same question? → use that.
2. Are you computing ≥ 3 indicators on the same ticker? → definitely use the local pattern.
3. Are you sweeping a watchlist (≥ 3 tickers)? → definitely use the local pattern (3 tickers × 8 indicators = 24 calls = full daily quota).
4. Single indicator on a single ticker for a one-off check? → fine to use the dedicated endpoint.

## When to use the analytics endpoints instead

For volatility / drawdown / correlation work across multiple tickers, prefer `analytics_fixed_window` over per-ticker indicator calls. See [risk-analytics.md](risk-analytics.md).
