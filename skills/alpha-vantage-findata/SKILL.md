---
name: alpha-vantage-findata
description: Global market data — quotes, OHLCV history (raw + split/dividend adjusted), 30+ technical indicators, financial statements, earnings (with call transcripts), news + sentiment scoring, FX, crypto, commodities, macro indicators, and server-side portfolio analytics (vol / drawdown / correlation / beta) — via the marketdata-cli wrapper around Alpha Vantage's official REST API. Covers US, EU, and Asia markets with stable, GAAP-normalized output.
metadata: {"openclaw":{"requires":{"bins":["marketdata-cli"],"env":["ALPHAVANTAGE_API_KEY"]},"install":[{"id":"marketdata-cli","kind":"pip","package":"marketdata-cli","bins":["marketdata-cli"],"label":"Install marketdata-cli"}]}}
---

# Alpha Vantage Financial Data

A market-data skill backed by [Alpha Vantage's official REST API](https://www.alphavantage.co/documentation/), accessed through the [`marketdata-cli`](https://pypi.org/project/marketdata-cli/) command-line tool. Every operation is a direct `marketdata-cli <command>` invocation. Output is the raw Alpha Vantage JSON envelope.

## Mindset: maximize this skill when it's enabled

If this skill is enabled on your workspace, **treat it as the primary source for every market data need it can cover** — not as a fallback. The catalog below is intentionally comprehensive: stocks, fundamentals, technicals, news+sentiment, FX, crypto, commodities, macro, **and** server-side portfolio analytics. For each task, your job is to find the *one or two commands* that satisfy the request without burning the daily quota — every section below has a "Best pattern" callout for that.

The only things this skill genuinely **cannot** provide are listed in the "Honest gaps" section at the bottom. For those, fall back to another data source.

## Setup (run once per workspace)

This skill depends on the `marketdata-cli` Python package and an Alpha Vantage API key. Both are **not** preinstalled in the gateway image.

```bash
# 1. Install the CLI into the gateway venv (bind-mounted, persists across tasks)
uv pip install marketdata-cli

# 2. Get a free API key at https://www.alphavantage.co/support/#api-key
#    (~20s, no credit card)

# 3. Export the key so every command picks it up automatically
export ALPHAVANTAGE_API_KEY=your_key_here
```

Verify with `marketdata-cli global_quote IBM` — you should see a JSON `Global Quote` block. If the key is missing or invalid, Alpha Vantage returns `{"Information": "..."}` instead.

You can also pass the key per-call with `-k your_key` if you don't want to export it.

## Output format

`marketdata-cli` emits **raw Alpha Vantage JSON to stdout** for every command. Common envelope shapes:

- **GLOBAL_QUOTE** → `{"Global Quote": {"01. symbol": "...", "05. price": "...", ...}}`
- **TIME_SERIES_DAILY[_ADJUSTED]** → `{"Meta Data": {...}, "Time Series (Daily)": {"YYYY-MM-DD": {"1. open": "...", ..., "5. adjusted close": "...", "7. dividend amount": "...", "8. split coefficient": "..."}}}`
- **OVERVIEW** → flat dict: `{"Symbol": "AAPL", "MarketCapitalization": "...", "PERatio": "...", ...}`
- **INCOME_STATEMENT / BALANCE_SHEET / CASH_FLOW** → `{"symbol": "...", "annualReports": [...], "quarterlyReports": [...]}`
- **NEWS_SENTIMENT** → `{"items": "...", "feed": [{title, summary, url, time_published, overall_sentiment_score, overall_sentiment_label, ticker_sentiment: [{ticker, relevance_score, ticker_sentiment_score, ticker_sentiment_label}]}]}`
- **SYMBOL_SEARCH** → `{"bestMatches": [{"1. symbol": "...", "2. name": "...", ...}]}`
- **EARNINGS** → `{"symbol": "...", "annualEarnings": [{fiscalDateEnding, reportedEPS}], "quarterlyEarnings": [{fiscalDateEnding, reportedDate, reportedEPS, estimatedEPS, surprise, surprisePercentage}]}`
- **ANALYTICS_FIXED_WINDOW** → `{"meta_data": {...}, "payload": {"RETURNS_CALCULATIONS": {"MEAN": {"AAPL": 0.001, ...}, "STDDEV(ANNUALIZED=TRUE)": {...}, "MAX_DRAWDOWN": {...}, "CORRELATION": {"index": [...], "correlation": [[...]]}}}}`
- **ANALYTICS_SLIDING_WINDOW** → similar shape with `RUNNING_*` keys (one entry per window step)
- **Indicator endpoints** (RSI, MACD, SMA, …) → `{"Meta Data": {...}, "Technical Analysis: <NAME>": {"YYYY-MM-DD": {<indicator-fields>}}}`

### Error envelopes (always check first)

When Alpha Vantage rejects a call, the JSON contains one of:

| Envelope | Meaning | Action |
|---|---|---|
| `{"Note": "Thank you for using Alpha Vantage! Our standard API call frequency is..."}` | Per-minute rate limit hit (5 req/min on free tier) | Wait 60s and retry |
| `{"Information": "...rate limit... 25 requests per day..."}` | Daily quota exhausted (25 req/day on free tier) | Wait 24h or upgrade |
| `{"Information": "...demo API key..."}` | API key invalid or using `demo` | Set a real `ALPHAVANTAGE_API_KEY` |
| `{"Error Message": "Invalid API call..."}` | Bad symbol, bad function, or bad parameters | Check the command and arguments |

Always check for one of these top-level keys before parsing the data block.

# Per-role playbooks

These are the "best pattern" recipes — start here when you're acting in one of the standard analyst roles.

## Market Data Analyst — quotes, OHLCV, validation

**Best pattern**: pull adjusted daily history once, then derive everything else locally.

```bash
# Spot quote (one symbol per call on free tier)
marketdata-cli global_quote AAPL

# Premium: bulk realtime quotes (up to 100 symbols, one call)
marketdata-cli realtime_bulk_quotes AAPL,MSFT,GOOGL,NVDA,TSLA

# Daily OHLCV — PREFER THE ADJUSTED SERIES for any historical analysis
# (the adjusted close back-corrects splits and dividends; the raw close does not)
marketdata-cli time_series_daily_adjusted AAPL -o full
marketdata-cli time_series_daily          AAPL -o full   # raw, only for tick reconciliation

# Intraday — required interval: 1min | 5min | 15min | 30min | 60min
marketdata-cli time_series_intraday AAPL -i 5min -o full --extended_hours

# Weekly / monthly (always returns full history; no -o flag)
marketdata-cli time_series_weekly_adjusted  AAPL
marketdata-cli time_series_monthly_adjusted AAPL

# Symbol resolution
marketdata-cli symbol_search -e "tencent"

# Corporate actions (separate from the adjusted series; useful for event studies)
marketdata-cli dividends AAPL
marketdata-cli splits    AAPL
```

**Validation in code-exec**: Alpha Vantage doesn't pre-compute a quality block. After parsing the `Time Series (Daily)` dict, check in `code-exec` for: (1) gaps between consecutive business days, (2) `high < low` or `close ∉ [low, high]`, (3) duplicate timestamps, (4) missing keys. Surface a `quality` block alongside the bars in your output.

**Freshness caveat**: free-tier `global_quote` returns the previous close even during market hours. For sub-15-minute freshness you need a premium plan or a separate realtime source.

## Technical Analyst — indicators

**Best pattern**: pull `time_series_daily_adjusted -o full` ONCE (1 call), then compute every indicator locally in `code-exec` from that single bar series. Calling individual indicator endpoints separately burns 1 quota slot per indicator per ticker — an 8-indicator dump on 5 tickers is 40 calls and exceeds the daily limit.

```bash
# THE one-call pattern
marketdata-cli time_series_daily_adjusted NVDA -o full
# → feed the "Time Series (Daily)" block into code-exec and compute:
#     SMA(9/21/50/200), EMA(9/21), RSI(14), MACD(12,26,9), Stochastic(14,3),
#     ADX(14), ATR(14), Bollinger(20,2), OBV, VWAP, Fibonacci retracements,
#     golden/death cross detection, support/resistance from recent highs/lows
```

**Per-indicator endpoint catalog** (use only when you need a single indicator and want Alpha Vantage's reference values):

| Category | Commands |
|---|---|
| Moving averages | `sma`, `ema`, `wma`, `dema`, `tema`, `trima`, `kama`, `mama`, `t3` |
| Oscillators (momentum) | `rsi`, `stoch`, `stochf`, `stochrsi`, `willr`, `cci`, `cmo`, `mom`, `roc`, `rocr`, `mfi`, `ultosc`, `bop` |
| MACD family | `macd`, `macdext`, `ppo`, `apo` |
| Trend / DMI | `adx`, `adxr`, `dx`, `plus_di`, `minus_di`, `plus_dm`, `minus_dm`, `aroon`, `aroonosc`, `trix`, `sar` |
| Volatility | `atr`, `natr`, `trange`, `bbands`, `midpoint`, `midprice` |
| Volume | `obv`, `vwap`, `ad`, `adosc` |
| Hilbert Transform | `ht_trendline`, `ht_sine`, `ht_trendmode`, `ht_dcperiod`, `ht_dcphase`, `ht_phasor` |

Common flag pattern for any indicator: `marketdata-cli <indicator> SYMBOL -i daily --time_period 14 --series_type close`. Run `marketdata-cli <indicator> --help` for endpoint-specific flags.

**Multi-timeframe pattern**: pull `time_series_intraday SYMBOL -i 60min -o full` for the hourly view alongside `time_series_daily_adjusted SYMBOL` for the daily. Two calls cover both timeframes.

## Fundamental Analyst — financials, valuation, macro

**Best pattern (single ticker workup, ~5 calls)**:

```bash
marketdata-cli company_overview   AAPL    # P/E, P/S, PEG, EV/EBITDA, ROE, ROA, beta, dividend yield, 52w range, EPS, sector, industry, analyst target price
marketdata-cli income_statement   AAPL    # annual + quarterly
marketdata-cli balance_sheet      AAPL    # annual + quarterly
marketdata-cli cash_flow          AAPL    # annual + quarterly
marketdata-cli earnings           AAPL    # reported EPS vs estimates, surprise %
```

**Deep research (when sentiment matters)**:

```bash
# Earnings call transcripts (15+ years of history) — has built-in LLM sentiment scoring
marketdata-cli earnings_call_transcript AAPL -q 2024Q3

# Forward EPS / revenue estimates (premium-only on free tier)
marketdata-cli earnings_estimates AAPL

# Distribution events
marketdata-cli dividends            AAPL
marketdata-cli splits               AAPL
marketdata-cli insider_transactions AAPL

# ETF holdings (when analyzing sector / thematic exposure)
marketdata-cli etf_profile XLF
```

**Macro coverage — Alpha Vantage replaces web-search for macro indicators**:

```bash
# Growth & inflation
marketdata-cli real_gdp
marketdata-cli real_gdp_per_capita
marketdata-cli cpi
marketdata-cli inflation
marketdata-cli retail_sales
marketdata-cli durables

# Labor
marketdata-cli unemployment
marketdata-cli nonfarm_payroll

# Monetary policy
marketdata-cli federal_funds_rate
marketdata-cli treasury_yield
```

When the user asks for "the macro backdrop", a 4-5 call sweep (`real_gdp` + `cpi` + `unemployment` + `federal_funds_rate` + `treasury_yield`) gives a full picture. **Do not** reach for web-search for these — Alpha Vantage has them natively.

**Calendar / market structure**:

```bash
marketdata-cli earnings_calendar      # upcoming earnings, all symbols
marketdata-cli ipo_calendar           # upcoming IPOs
marketdata-cli listing_status         # active or delisted US stocks/ETFs
marketdata-cli market_status          # current exchange open/close status
marketdata-cli top_gainers_losers     # daily movers (top 20 each)
```

## Sentiment Analyst — news with built-in NLP scoring

**Best pattern**: a single `news_sentiment` call with multiple tickers gives headlines AND per-article sentiment scores in one quota slot.

```bash
# Multi-ticker batched news + sentiment in 1 call (the killer feature)
marketdata-cli news_sentiment --tickers AAPL,MSFT,NVDA --sort LATEST --limit 50

# Topic-filtered (earnings, m&a, ipo, financial_markets, economy_macro, ...)
marketdata-cli news_sentiment --tickers AAPL --topics earnings --limit 20

# Historical news window
marketdata-cli news_sentiment --tickers AAPL --time_from 20260301T0000 --time_to 20260331T2359 --limit 100
```

Each article in the `feed` array carries:
- `overall_sentiment_score` — float in [-1, 1] for the whole article
- `overall_sentiment_label` — `Bearish` | `Somewhat-Bearish` | `Neutral` | `Somewhat-Bullish` | `Bullish`
- `ticker_sentiment[]` — per-ticker `relevance_score` (0–1) + `ticker_sentiment_score` + `ticker_sentiment_label`

**Use these directly instead of running your own sentiment classifier** on the headlines. This is a real upgrade over yfinance, which only returns headline strings.

**Insider flow** (smart-money signal):

```bash
marketdata-cli insider_transactions AAPL
```

**Earnings call sentiment** (LLM-tagged transcripts — cannot get this from yfinance at all):

```bash
marketdata-cli earnings_call_transcript NVDA -q 2024Q4
```

**Market-fear / volatility proxy** (Alpha Vantage doesn't expose `^VIX` on the free tier — use ETF proxies instead):

```bash
marketdata-cli time_series_daily_adjusted VIXY    # iPath VIX short-term ETF
marketdata-cli time_series_daily_adjusted UVXY    # ProShares VIX short-term (2x)
marketdata-cli time_series_daily_adjusted VXX     # iPath VIX (delisted in US — check listing_status)
```

## Risk Manager — server-side portfolio analytics

**Best pattern**: use `analytics_fixed_window` to compute the entire risk panel for an N-stock portfolio in **one call**. Use `analytics_sliding_window` for rolling-window metrics like HV30 / HV60.

This is the single most quota-efficient endpoint in Alpha Vantage for risk work — it replaces what would otherwise be N separate `time_series_daily` pulls plus local computation.

### `analytics_fixed_window` — full portfolio risk in one call

```bash
# 5-stock portfolio risk panel: mean returns, annualized vol, max drawdown, correlation matrix
marketdata-cli analytics_fixed_window \
  -s AAPL,MSFT,NVDA,TSLA,SPY \
  -r 1year \
  -i DAILY \
  -o close \
  -c "MEAN,STDDEV(annualized=True),MAX_DRAWDOWN,CORRELATION"
```

Available calculations (pass any combination as a comma-separated `-c` list):

| Calculation | Meaning |
|---|---|
| `MIN`, `MAX` | Period extremes |
| `MEAN`, `MEDIAN` | Average / median return |
| `CUMULATIVE_RETURN` | Total return over the window |
| `VARIANCE`, `VARIANCE(annualized=True)` | Variance of returns |
| `STDDEV`, `STDDEV(annualized=True)` | **Standard deviation = realized volatility** |
| `MAX_DRAWDOWN` | Worst peak-to-trough drawdown |
| `HISTOGRAM(bins=N)` | Return distribution |
| `AUTOCORRELATION(lag=N)` | Serial dependence |
| `COVARIANCE` | N×N covariance matrix |
| `CORRELATION` | N×N correlation matrix (Pearson by default) |

Range param (`-r`): a duration like `5month`, `1year`, `2year`, `5year`, `10year`, or specific dates.
Interval (`-i`): `1min` / `5min` / `15min` / `30min` / `60min` / `DAILY` / `WEEKLY` / `MONTHLY`.
OHLC (`-o`): `open` / `high` / `low` / `close` (default `close`).

### `analytics_sliding_window` — HV30, HV60, rolling beta

```bash
# Rolling 30-day annualized vol (= HV30) over 1 year of history
marketdata-cli analytics_sliding_window \
  -s AAPL \
  -r 1year \
  -i DAILY \
  -w 30 \
  -o close \
  -c "STDDEV(annualized=True)"

# Rolling 60-day vol
marketdata-cli analytics_sliding_window \
  -s AAPL \
  -r 1year \
  -i DAILY \
  -w 60 \
  -o close \
  -c "STDDEV(annualized=True)"

# Rolling 90-day correlation between a stock and SPY (use to detect regime shifts)
marketdata-cli analytics_sliding_window \
  -s AAPL,SPY \
  -r 2year \
  -i DAILY \
  -w 90 \
  -o close \
  -c "CORRELATION"
```

### Beta computation

Alpha Vantage doesn't return a single "beta" number directly, but `analytics_fixed_window` gives you the inputs to compute it server-side in one call:

```bash
# Pass TICKER + SPY, request CORRELATION + STDDEV → derive beta
marketdata-cli analytics_fixed_window \
  -s AAPL,SPY \
  -r 2year \
  -i DAILY \
  -o close \
  -c "STDDEV,CORRELATION"
# Then: beta = correlation(AAPL, SPY) × stddev(AAPL) / stddev(SPY)
# (or use COVARIANCE / VARIANCE(SPY) for the same thing)
```

### Direct ATR for stop-distance

```bash
marketdata-cli atr AAPL -i daily --time_period 14
# Stop distance ≈ 1.5–2.0 × ATR(14)
```

## Symbol conventions

| Asset class | Examples | Notes |
|---|---|---|
| US Stocks | `AAPL`, `MSFT`, `IBM`, `NVDA`, `TSLA` | Standard tickers |
| Foreign equities | `TSCO.LON`, `SHOP.TRT`, `RELIANCE.BSE`, `600519.SHH`, `000001.SHZ` | `SYMBOL.EXCHANGE` format — `.LON` (London), `.TRT` (Toronto), `.BSE` (Bombay), `.SHH` (Shanghai), `.SHZ` (Shenzhen) |
| ETFs | `SPY`, `QQQ`, `XLF`, `XLE`, `XLK`, `EEM`, `IWM`, `VIXY` | Treat as regular tickers |
| Sector proxies | `XLF` finance, `XLE` energy, `XLK` tech, `XLV` health, `XLP` staples, `XLY` discretionary, `XLI` industrials, `XLB` materials, `XLU` utilities, `XLC` comms, `XLRE` real estate | Use these as sector-rotation signals when no sector index is available |
| Indices | (premium-only on free tier) | Use SPY / QQQ / IWM as proxies; VIX → VIXY/UVXY |
| Forex | Pairs via `--from_currency` / `--to_currency` (spot) or `--from_symbol` / `--to_symbol` (time series) | Not standard ticker form |
| Crypto | `--symbol BTC --market USD` | Pair format, not `BTC-USD` |
| Commodities | Dedicated endpoints (`brent`, `wti`, `natural_gas`, `copper`, `gold_silver_spot`, …) | No symbol — endpoint is the asset |

## Forex, crypto, commodities — quick command reference

### Forex

```bash
marketdata-cli currency_exchange_rate --from_currency USD --to_currency JPY
marketdata-cli fx_intraday   --from_symbol EUR --to_symbol USD -i 5min
marketdata-cli fx_daily      --from_symbol EUR --to_symbol USD
marketdata-cli fx_weekly     --from_symbol EUR --to_symbol USD
marketdata-cli fx_monthly    --from_symbol EUR --to_symbol USD
```

### Crypto

```bash
marketdata-cli digital_currency_daily   --symbol BTC --market USD
marketdata-cli digital_currency_weekly  --symbol BTC --market USD
marketdata-cli digital_currency_monthly --symbol BTC --market USD
marketdata-cli crypto_intraday          --symbol ETH --market USD -i 5min
```

### Commodities

```bash
marketdata-cli wti
marketdata-cli brent
marketdata-cli natural_gas
marketdata-cli gold_silver_spot
marketdata-cli gold_silver_history
marketdata-cli copper
marketdata-cli aluminum
marketdata-cli wheat
marketdata-cli corn
marketdata-cli cotton
marketdata-cli sugar
marketdata-cli coffee
```

## Limits and caveats

- **Free tier: 5 requests per minute, 25 requests per day.** Hard caps. Plan call budgets accordingly.
- **End-of-day data only on free tier.** `global_quote` returns the latest *closing* price, not real-time. Real-time / intraday-delayed data and `realtime_bulk_quotes` require a premium plan.
- **Per-indicator endpoints cost 1 call each.** Always prefer the "one OHLCV pull + local computation" pattern in the Technical Analyst playbook for multi-indicator work.
- **`analytics_fixed_window` is the highest-leverage endpoint** for portfolio work — N-stock × M-calculation panels in one call. Use it whenever you need vol / drawdown / correlation for more than one ticker.
- **Use the adjusted price series for any historical analysis** — `time_series_daily_adjusted` etc. The unadjusted versions don't back-correct splits and dividends and will produce misleading returns / vol / drawdown numbers.
- **Fundamentals refresh daily** after the company's latest filing. Field names are GAAP-normalized and stable across companies (`totalRevenue`, `netIncome`, `operatingCashflow`, …).
- **Demo key (`-k demo`)** only works for a tiny set of IBM endpoints. Get a free key from https://www.alphavantage.co/support/#api-key for real work.

## Honest gaps (what Alpha Vantage doesn't expose)

When the agent asks for something in this list, surface "not available from Alpha Vantage" rather than fabricating it. If the workspace also has the `yahoo-finance` skill, those gaps can be filled by `analyst.py`, `holders.py`, `options.py`, etc. If not, surface the gap to the user.

| Need | Status | Notes |
|---|---|---|
| Analyst recommendation distribution / upgrades / downgrades | ❌ | OVERVIEW exposes only a single `AnalystTargetPrice` number |
| Institutional ownership / 13F filings | ❌ | Not exposed at any tier |
| Options chains (free) | ❌ | `historical_options` and `realtime_options` are premium-only |
| Tick-level / Level-2 / order book | ❌ | Not exposed at any tier |
| Real Fear & Greed Index (CNN) | ❌ | Proprietary; use a VIX-tracking ETF (`VIXY`) as a substitute |
| Put/call ratios | ❌ | Requires options data (premium-only) |
| Social-media sentiment (X / Reddit / StockTwits) | ❌ | Out of scope for Alpha Vantage |
| Fund flows (mutual fund / ETF) | ❌ | Not exposed |
| Short interest | ❌ | Not exposed |
| PPI inflation | ❌ | Only CPI is exposed |
| Sector-aggregate indices | ⚠️ Use ETF proxies (`XLF`, `XLE`, `XLK`, …) |

## Playbook references

When a task lines up with one of the standard analyst roles, drill into the matching playbook for deeper recipes and worked examples:

- [references/risk-analytics.md](references/risk-analytics.md) — `analytics_fixed_window` / `analytics_sliding_window` patterns for portfolio vol, drawdown, beta, correlation. **Start here for any Risk Manager work.**
- [references/technicals.md](references/technicals.md) — full 30+ indicator catalog and the one-pull-plus-local-computation pattern.
- [references/fundamentals.md](references/fundamentals.md) — single-ticker workup recipe + macro coverage that replaces web-search.
- [references/news-sentiment.md](references/news-sentiment.md) — `news_sentiment` workflows, sentiment-extreme detection, divergence patterns, earnings-call transcript usage.
- [references/comparison.md](references/comparison.md) — multi-stock comparison patterns, including the one-call sector rotation recipe.
- [references/forex-crypto.md](references/forex-crypto.md) — FX and crypto endpoints.
- [references/macro.md](references/macro.md) — full macro endpoint reference.

## Quick reference — common flags

| Flag | Meaning |
|---|---|
| `-k, --api-key` | Override `ALPHAVANTAGE_API_KEY` env var for one call |
| `-h, --help` | Show help for any command (e.g. `marketdata-cli rsi --help`) |
| `-v, --verbose` | Enable verbose logging |
| `-d, --datatype` | `json` (default) or `csv` |
| `-o, --outputsize` | `compact` (last 100 bars) or `full` (20+ years) — daily/intraday only |
| `-i, --interval` | `1min`/`5min`/`15min`/`30min`/`60min`/`daily`/`weekly`/`monthly` (depends on command) |
| `-s, --symbols` | Comma-separated symbols (analytics + bulk quotes only) |
| `-r, --range_param` | Duration (`5month`, `1year`, `2year`) or date — analytics only |
| `-c, --calculations` | Comma-separated calculation list — analytics only |
| `-w, --window_size` | Rolling window size — sliding analytics only |

Run `marketdata-cli --help` for the full list of 100+ commands, or `marketdata-cli <command> --help` for the exact flag set of any one.
