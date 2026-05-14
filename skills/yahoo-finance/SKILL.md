---
name: yahoo-finance
description: Canonical source of structured market data — quotes, OHLCV history, technical indicators, financial statements, valuation multiples, earnings, analyst targets, holders, news, options chains, and historical volatility — via CLI scripts under scripts/. Prefer this skill over web-search for any quantitative market data on stocks, ETFs, indices, crypto, forex, and futures.
metadata: {"openclaw":{"requires":{"bins":["python3"]},"install":[{"id":"yfinance","kind":"pip","package":"yfinance","bins":[],"label":"Install yfinance"},{"id":"pandas","kind":"pip","package":"pandas","bins":[],"label":"Install pandas"},{"id":"numpy","kind":"pip","package":"numpy","bins":[],"label":"Install numpy"}]}}
---

# Yahoo Finance

A production market-data skill backed by [`yfinance`](https://ranaroussi.github.io/yfinance/). Every operation is a self-contained CLI script under `scripts/` that returns either human-readable text or — with `--json` — a strict, machine-parseable JSON object suitable for downstream agents.

## Setup (run once per workspace)

This skill depends on three Python packages that are **not** preinstalled in the gateway image. Before invoking any script for the first time, install them into the gateway's venv:

```bash
uv pip install yfinance pandas numpy
```

Run this once per workspace — the venv is bind-mounted, so subsequent script invocations (and subsequent tasks) reuse it. If you skip this step the scripts exit 1 with a clear `ERROR: <pkg> is not installed. Run: pip install <pkg>` message; the same install command above resolves it.

## When to use

- **Prefer this skill over `web-search`** for any quantitative market data (prices, fundamentals, earnings, options, holders, volatility). Web-search should only be used for context yfinance does not supply: macro indicators, regulatory filings, social-media sentiment, qualitative news beyond headlines.
- The skill covers stocks, ETFs, mutual funds, indices, crypto (`BTC-USD`), forex (`EURUSD=X`), and futures (`GC=F`).
- Data is delayed ~15–20 minutes for free Yahoo endpoints.

## Output contract

Every script:

1. Defaults to **human-readable text** on stdout.
2. With `--json`, prints a single JSON object on stdout. Errors are also surfaced inside the JSON payload as `{"error": "...", "ticker": "..."}` (and printed to stderr). **Never parse human mode programmatically.**
3. In `--json` mode, exits 0 even on per-ticker errors so batch callers can keep going. In human mode, exits non-zero on hard failures.
4. All numerics rounded to 4 decimals; `NaN`/`inf` → `null`; `pandas.Timestamp` → ISO8601.

## Script catalog

| Script | Purpose | Key flags | Best for |
|---|---|---|---|
| `quote.py TICKERS…` | Current price, day range, volume, market cap, change% | `--json` | Market Data, Trading Assistant |
| `history.py TICKER` | OHLCV history with optional gap/OHLC validation | `--period 1y --interval 1d --validate --json` `--start --end` `--csv PATH` `--limit N` | Market Data, Technical, Risk |
| `indicators.py TICKER` | RSI, MACD, Stochastic, ADX, ATR, SMA/EMA, Fib, signal summary | `--period 6mo --interval 1d --ma 9,21,50,200 --json` | Technical |
| `financials.py TICKER` | Income statement / balance sheet / cash flow | `--statement income\|balance\|cashflow --period annual\|quarterly\|ttm --json` | Fundamental |
| `valuation.py TICKER` | P/E, P/S, PEG, EV/EBITDA, margins, ROE, beta, 52w range, dividend yield | `--json` | Fundamental |
| `earnings.py TICKER` | Next earnings date, history, EPS/revenue estimates, EPS revisions, growth | `--json` | Fundamental |
| `analyst.py TICKER` | Price targets, recommendations, recent upgrades/downgrades | `--json` | Fundamental, Sentiment |
| `holders.py TICKER` | Major / institutional / mutual fund holders, insider transactions | `--json` | Sentiment |
| `news.py TICKER` | Recent headlines (normalized across yfinance schema versions) | `--limit 10 --json` | Sentiment |
| `options.py TICKER` | Option chain (calls + puts) for an expiration; or list expirations | `--list-expirations` `--expiration YYYY-MM-DD` `--json` | Strategy, Risk |
| `volatility.py TICKER` | Realized vol, ATR, drawdown, beta vs SPY + sizing hints | `--lookback 60 --json` | Risk |
| `search.py QUERY` | Find ticker symbols by company name or partial match | `--limit 10 --json` | Market Data, Trading Assistant |

The shared helpers (`scripts/_yf.py`) handle yfinance/pandas/numpy import guards, JSON encoding for Timestamp/NaN/DataFrame, and the error contract — do not invoke directly.

## Worked examples

### Market Data Analyst — fetch + validate OHLCV

```bash
python3 scripts/quote.py AAPL MSFT NVDA TSLA --json
python3 scripts/history.py AAPL --period 6mo --interval 1d --validate --json
```

The `--validate` flag returns a `quality` block with `gaps`, `ohlc_violations`, `duplicate_bars`, and `missing_pct`. **Always run with `--validate`** before passing data to downstream analysts.

### Technical Analyst — indicators in one call

```bash
python3 scripts/indicators.py NVDA --period 6mo --interval 1d --json
```

Returns RSI(14), MACD(12,26,9), Stochastic(14,3), ADX(14), ATR(14)+ATR%, all four canonical SMAs, EMA(9,21), golden/death cross flags, Fibonacci retracements, and a `signal_summary` of `BUY|HOLD|SELL` with `confidence` in `[0,1]`. The signal is a baseline heuristic — override with your own analysis when conviction differs.

### Fundamental Analyst — full picture in 4 calls

```bash
python3 scripts/valuation.py MSFT --json
python3 scripts/financials.py MSFT --statement income --period quarterly --json
python3 scripts/earnings.py MSFT --json
python3 scripts/analyst.py MSFT --json
```

### Sentiment Analyst — news + flow

```bash
python3 scripts/news.py NVDA --limit 20 --json
python3 scripts/analyst.py NVDA --json    # rec trends, upgrades/downgrades
python3 scripts/holders.py NVDA --json    # institutional + insider activity
```

### Risk Manager — sizing inputs

```bash
python3 scripts/volatility.py AAPL --lookback 60 --json
```

Returns `atr14`, `atr14_pct`, realized vol, downside deviation, max drawdown, and beta-vs-SPY. The Risk Manager should use `atr14` to set stop distances (typically 1.5–2.0×ATR) and realized vol to size positions inversely to volatility.

### Strategy / Risk — options chain

```bash
python3 scripts/options.py SPY --list-expirations --json
python3 scripts/options.py SPY --expiration 2026-04-17 --json
```

## Symbol conventions

| Asset class | Examples |
|---|---|
| US Stocks | `AAPL`, `MSFT`, `GOOGL`, `AMZN`, `TSLA`, `META`, `NVDA` |
| Indices | `^GSPC` (S&P 500), `^DJI` (Dow), `^IXIC` (NASDAQ), `^RUT` (Russell 2000), `^VIX` |
| Crypto | `BTC-USD`, `ETH-USD`, `SOL-USD`, `DOGE-USD` |
| Forex | `EURUSD=X`, `GBPUSD=X`, `USDJPY=X` |
| Futures | `GC=F` (Gold), `CL=F` (Oil), `SI=F` (Silver), `ES=F` (S&P E-mini) |
| Foreign equities | `7203.T` (Toyota Tokyo), `BABA` (NYSE ADR), `0700.HK` (Tencent HK) |

## Limits and caveats

- Free-tier data is delayed ~15–20 minutes during market hours.
- yfinance rate-limits aggressive callers — **batch** via `quote.py SYM1 SYM2 SYM3` instead of looping over `quote.py SYM1; quote.py SYM2; …`.
- `quote.py` uses `fast_info` first (cheap) and only falls back to the heavier `info` call when needed; prefer it over `valuation.py` for simple price lookups.
- Some data is unavailable for certain instruments (e.g. crypto has no `financials`, indices have no `holders`). Scripts return `{"error": "..."}` rather than crashing — consumers should check for `error` in any JSON response.
- Indicator math in `indicators.py` is implemented in pure pandas/numpy — no TA-Lib dependency.
