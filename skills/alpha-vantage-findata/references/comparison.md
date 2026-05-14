# Sector / Multi-Stock Comparison

**Goal:** Compare fundamentals, technicals, or risk metrics across several companies to find the strongest pick.

## 1. Cross-stock risk panel — 1 call (the killer pattern)

Use `analytics_fixed_window` with multiple symbols to get the entire comparative risk picture in **one quota slot**:

```bash
marketdata-cli analytics_fixed_window \
  -s AAPL,MSFT,GOOGL,META,NVDA \
  -r 1year \
  -i DAILY \
  -o close \
  -c "MEAN,STDDEV(annualized=True),MAX_DRAWDOWN,CUMULATIVE_RETURN,CORRELATION"
```

The response gives you, for all 5 stocks at once:

- Average daily return
- Annualized realized volatility
- Worst peak-to-trough drawdown
- Total return over the window
- 5×5 correlation matrix (for diversification analysis)

This is the **fastest path** to a sector / watchlist comparison. See [risk-analytics.md](risk-analytics.md) for the full calculation list and rolling-window variant.

## 2. Side-by-side fundamentals

Each `company_overview` call costs 1 quota slot. A 3-stock comparison runs 3 calls:

```bash
marketdata-cli company_overview AAPL
marketdata-cli company_overview MSFT
marketdata-cli company_overview GOOGL
```

Compare these fields across the responses:

- `PERatio`, `ForwardPE`, `PriceToSalesRatioTTM`, `PEGRatio`, `EVToEBITDA`
- `OperatingMarginTTM`, `ProfitMargin`, `ReturnOnEquityTTM`, `ReturnOnAssetsTTM`
- `QuarterlyRevenueGrowthYOY`, `QuarterlyEarningsGrowthYOY`
- `Beta`, `DividendYield`, `52WeekHigh`, `52WeekLow`
- `AnalystTargetPrice` vs current price → upside/downside potential

## 3. Side-by-side earnings

```bash
marketdata-cli earnings AAPL
marketdata-cli earnings MSFT
marketdata-cli earnings GOOGL
```

Compare the most recent quarter's `surprisePercentage` and the trend across the last 4 quarters.

## 4. Side-by-side technicals

For multi-indicator comparison across multiple tickers, **don't** call individual indicator endpoints — that explodes the quota. Either:

**Option A — analytics endpoint** (1 call for vol/drawdown/correlation across N tickers):

```bash
marketdata-cli analytics_fixed_window \
  -s AAPL,MSFT,GOOGL \
  -r 6month \
  -i DAILY \
  -o close \
  -c "STDDEV(annualized=True),MAX_DRAWDOWN,CORRELATION"
```

**Option B — pull adjusted history per ticker** (N calls, then compute every indicator locally):

```bash
marketdata-cli time_series_daily_adjusted AAPL -o full
marketdata-cli time_series_daily_adjusted MSFT -o full
marketdata-cli time_series_daily_adjusted GOOGL -o full
# Feed all three into code-exec and compute RSI / MACD / SMA / etc. on each
```

## 5. Longer-term comparison (multi-year)

Weekly or monthly adjusted bars span 20+ years on the free tier:

```bash
marketdata-cli time_series_weekly_adjusted  AAPL
marketdata-cli time_series_weekly_adjusted  MSFT
marketdata-cli time_series_monthly_adjusted AAPL    # for decade-scale view
```

Always use the `_adjusted` variants for multi-year work — splits and dividends will distort the unadjusted close.

## 6. Side-by-side quotes (rate-limit aware)

`global_quote` accepts only one symbol per call. A 5-ticker watchlist sweep costs 5 of your 25 daily calls and risks the 5/min limit:

```bash
marketdata-cli global_quote AAPL
marketdata-cli global_quote MSFT
marketdata-cli global_quote GOOGL
marketdata-cli global_quote META
marketdata-cli global_quote NVDA
```

**For premium users**, `realtime_bulk_quotes` fetches up to 100 symbols in a single call:

```bash
marketdata-cli realtime_bulk_quotes AAPL,MSFT,GOOGL,META,NVDA,TSLA,AMZN
```

## 7. Sector rotation comparison

Use the SPDR sector ETFs as sector proxies and compare them with the analytics endpoint:

```bash
marketdata-cli analytics_fixed_window \
  -s XLK,XLF,XLE,XLV,XLY,XLP,XLI,XLB,XLU,XLC,XLRE \
  -r 3month \
  -i DAILY \
  -o close \
  -c "CUMULATIVE_RETURN,STDDEV(annualized=True),MAX_DRAWDOWN"
```

One call gives you the relative performance, vol, and drawdown of every S&P sector. Sort by `CUMULATIVE_RETURN` to spot leaders and laggards.

Sector ETF reference:

| ETF | Sector |
|---|---|
| `XLK` | Technology |
| `XLF` | Financials |
| `XLE` | Energy |
| `XLV` | Health Care |
| `XLY` | Consumer Discretionary |
| `XLP` | Consumer Staples |
| `XLI` | Industrials |
| `XLB` | Materials |
| `XLU` | Utilities |
| `XLC` | Communication Services |
| `XLRE` | Real Estate |
