# Portfolio Risk Analytics

**Goal:** Compute volatility, drawdown, beta, and correlation for one stock or a multi-stock portfolio with the smallest possible quota footprint.

The `analytics_fixed_window` and `analytics_sliding_window` endpoints are Alpha Vantage's killer feature for risk work — they compute multiple metrics across multiple symbols **server-side in one call**. Use these instead of pulling N separate `time_series_daily` series and running the math locally.

## 1. Full portfolio risk panel — 1 call

Mean returns, annualized volatility, max drawdown, and the full correlation matrix for a 5-stock portfolio + benchmark, in a single API call:

```bash
marketdata-cli analytics_fixed_window \
  -s AAPL,MSFT,NVDA,TSLA,SPY \
  -r 1year \
  -i DAILY \
  -o close \
  -c "MEAN,STDDEV(annualized=True),MAX_DRAWDOWN,CORRELATION"
```

The response payload contains:

- `MEAN` — average daily return per symbol
- `STDDEV(ANNUALIZED=TRUE)` — annualized realized volatility per symbol (this is "vol" in everyday usage)
- `MAX_DRAWDOWN` — worst peak-to-trough drawdown over the window per symbol
- `CORRELATION` — N×N matrix indexed by symbol

That's the entire risk panel for an N-stock portfolio in **1 quota slot**, regardless of N (free-tier limit is roughly 5 symbols per call; check the response).

## 2. HV30 / HV60 — rolling realized volatility

For a single ticker, the rolling 30-day annualized volatility (HV30) over 1 year of history:

```bash
marketdata-cli analytics_sliding_window \
  -s AAPL \
  -r 1year \
  -i DAILY \
  -w 30 \
  -o close \
  -c "STDDEV(annualized=True)"
```

For HV60, change `-w 30` to `-w 60`. For HV90, `-w 90`. Each is one call.

The response gives a time series of vol estimates — use the latest value as the current HV, or chart the full series to see vol regime shifts.

## 3. Rolling correlation — regime detection

Watch how a stock's correlation to its sector or to SPY drifts over time:

```bash
# Rolling 90-day correlation between AAPL and SPY
marketdata-cli analytics_sliding_window \
  -s AAPL,SPY \
  -r 2year \
  -i DAILY \
  -w 90 \
  -o close \
  -c "CORRELATION"
```

Sharp drops in correlation often precede idiosyncratic moves (good for finding alpha-rich names); spikes often signal regime stress.

## 4. Beta computation

Alpha Vantage doesn't return a single "beta" number directly, but you can derive it server-side from one analytics call:

```bash
marketdata-cli analytics_fixed_window \
  -s AAPL,SPY \
  -r 2year \
  -i DAILY \
  -o close \
  -c "STDDEV,CORRELATION"
```

Then in `code-exec`:

```python
beta = correlation(AAPL, SPY) * stddev(AAPL) / stddev(SPY)
```

Or use `COVARIANCE` directly:

```bash
marketdata-cli analytics_fixed_window \
  -s AAPL,SPY \
  -r 2year \
  -i DAILY \
  -o close \
  -c "COVARIANCE,VARIANCE"
```

```python
beta = covariance(AAPL, SPY) / variance(SPY)
```

Both forms cost 1 quota slot.

## 5. Stop-loss distance (ATR)

For pre-trade stop sizing, the dedicated ATR endpoint is fine — 1 call per ticker:

```bash
marketdata-cli atr AAPL -i daily --time_period 14
```

Stop distance ≈ 1.5–2.0 × ATR(14). Pair with the ANNUALIZED stddev from the analytics endpoint to size positions inversely to volatility.

## Available calculations (full list)

Pass any combination as a comma-separated `-c` argument:

| Calculation | What it returns |
|---|---|
| `MIN`, `MAX` | Period extreme values |
| `MEAN`, `MEDIAN` | Average / median return |
| `CUMULATIVE_RETURN` | Total return over the window |
| `VARIANCE` | Variance of returns |
| `VARIANCE(annualized=True)` | Annualized variance |
| `STDDEV` | Standard deviation |
| `STDDEV(annualized=True)` | Annualized stddev = realized vol |
| `MAX_DRAWDOWN` | Worst peak-to-trough drawdown |
| `HISTOGRAM(bins=N)` | Return distribution histogram |
| `AUTOCORRELATION(lag=N)` | Serial correlation at lag N |
| `COVARIANCE` | N×N covariance matrix |
| `CORRELATION` | N×N correlation matrix (Pearson default) |
| `CORRELATION(method=KENDALL)` | Kendall rank correlation |
| `CORRELATION(method=SPEARMAN)` | Spearman rank correlation |

## Range and interval options

- `-r, --range_param` (`analytics_fixed_window`): one of `5month`, `1year`, `2year`, `5year`, `10year`, or specific dates
- `-i, --interval`: `1min`, `5min`, `15min`, `30min`, `60min`, `DAILY`, `WEEKLY`, `MONTHLY`
- `-o, --ohlc`: `open` / `high` / `low` / `close` (default `close` — almost always what you want for risk work)
- `-w, --window_size` (`analytics_sliding_window` only): integer, the rolling-window length in `interval` units

## Quota math vs. the local-computation alternative

| Approach | Calls for a 5-stock vol+drawdown+correlation panel |
|---|---|
| `analytics_fixed_window -s … -c STDDEV,MAX_DRAWDOWN,CORRELATION` | **1** |
| Per-ticker `time_series_daily_adjusted` + local code-exec math | 5 (one per ticker) |

The analytics endpoint is 5× more efficient for portfolio work and trivially extends to 10–15 calculations without additional quota cost.

## When to fall back to raw OHLCV + code-exec

Use `time_series_daily_adjusted SYMBOL -o full` plus local computation when:

- You need a custom risk metric the analytics endpoint doesn't support (e.g. CVaR, Sortino ratio, Calmar ratio, downside capture).
- You're computing single-ticker metrics where 1 OHLCV pull + local math is the same cost as 1 analytics call.
- You want to chart the full price history alongside the metrics.

Otherwise, prefer the analytics endpoint.
