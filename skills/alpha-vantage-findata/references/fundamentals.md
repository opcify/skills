# Fundamental Analysis

**Goal:** Evaluate a company's financial health, profitability, valuation, and the macro backdrop it operates in.

A full single-ticker workup runs 5–7 calls. The macro section (CPI, GDP, rates, employment) adds 4–5 more — but **all of it stays on Alpha Vantage**. Don't reach for web-search for macro — Alpha Vantage has it natively, and it's faster and more reliable.

## 1. Company overview

Sector, industry, market cap, P/E (trailing + forward), P/S, PEG, EV/EBITDA, ROE, ROA, beta, 52-week range, dividend yield, EPS, and analyst target price — all in one call:

```bash
marketdata-cli company_overview AAPL
```

## 2. Income statement

Revenue, gross profit, operating income, net income — both annual and quarterly history (newest first), GAAP-normalized:

```bash
marketdata-cli income_statement AAPL
```

## 3. Balance sheet

Total assets, total liabilities, shareholder equity, working capital, debt levels:

```bash
marketdata-cli balance_sheet AAPL
```

## 4. Cash flow

Operating, investing, and financing cash flows + free cash flow:

```bash
marketdata-cli cash_flow AAPL
```

## 5. Earnings

Reported EPS vs. estimates, surprise %, fiscal date ending, both annual and quarterly:

```bash
marketdata-cli earnings AAPL
```

## 6. Earnings call transcript (deep research)

Alpha Vantage exposes 15+ years of earnings call transcripts enriched with LLM-based sentiment scoring. This is data yfinance doesn't have at all — use it whenever the user wants management commentary, guidance changes, or tone shifts:

```bash
marketdata-cli earnings_call_transcript AAPL -q 2024Q3
```

## 7. Dividends, splits, insider activity

```bash
marketdata-cli dividends            AAPL
marketdata-cli splits               AAPL
marketdata-cli insider_transactions AAPL
```

## 8. ETF holdings (when analyzing sector / thematic exposure)

```bash
marketdata-cli etf_profile XLF    # financial sector ETF holdings
marketdata-cli etf_profile QQQ    # NASDAQ-100 holdings
marketdata-cli etf_profile EEM    # emerging markets ETF holdings
```

## 9. Macro backdrop (replaces web-search)

Alpha Vantage covers the standard US macro indicators natively. Use these instead of web-search:

### Growth & inflation

```bash
marketdata-cli real_gdp
marketdata-cli real_gdp_per_capita
marketdata-cli cpi
marketdata-cli inflation
marketdata-cli retail_sales
marketdata-cli durables
```

### Labor

```bash
marketdata-cli unemployment
marketdata-cli nonfarm_payroll
```

### Monetary policy

```bash
marketdata-cli federal_funds_rate
marketdata-cli treasury_yield
```

A typical "macro backdrop" sweep is 4–5 calls: `real_gdp` + `cpi` + `unemployment` + `federal_funds_rate` + `treasury_yield`.

## 10. Calendar / market structure

```bash
marketdata-cli earnings_calendar    # upcoming earnings, all symbols
marketdata-cli ipo_calendar         # upcoming IPOs
marketdata-cli listing_status       # active or delisted US stocks/ETFs
marketdata-cli market_status        # current global exchange open/close
marketdata-cli top_gainers_losers   # daily movers (top 20 each)
```

## What's not exposed

These are the only fundamental data points Alpha Vantage genuinely doesn't have. Surface "not available from Alpha Vantage" rather than fabricating:

- **Analyst recommendation distribution** (buy/hold/sell ratio, upgrades/downgrades). `company_overview` gives you `AnalystTargetPrice` (a single number) but not the distribution or revision history.
- **Forward EPS / revenue estimates** beyond the next quarter — `earnings_estimates` is premium-only.
- **Institutional ownership concentration / 13F filings** — not exposed.
- **PPI inflation** — only CPI is in the macro endpoint set.
- **Sector-aggregate indices** — use the sector ETF proxies (`XLF`, `XLE`, `XLK`, …) and pull `time_series_daily_adjusted` against them instead.
