# News & Sentiment

**Goal:** Read the news flow and sentiment landscape around a ticker, sector, or topic — without running your own NLP classifier.

Alpha Vantage's `news_sentiment` endpoint is the killer feature for this skill: it returns headlines from premier news outlets **with structured sentiment scoring already attached**. Use this directly instead of fetching headline strings and trying to classify them yourself.

## 1. Single-ticker sentiment in 1 call

```bash
marketdata-cli news_sentiment --tickers AAPL --limit 20
```

Each item in the `feed` array carries:

| Field | Meaning |
|---|---|
| `title`, `summary`, `url`, `source` | Standard headline metadata |
| `time_published` | `YYYYMMDDTHHMMSS` UTC timestamp |
| `topics[]` | List of `{topic, relevance_score}` |
| `overall_sentiment_score` | Float in `[-1, 1]` for the article as a whole |
| `overall_sentiment_label` | `Bearish` / `Somewhat-Bearish` / `Neutral` / `Somewhat-Bullish` / `Bullish` |
| `ticker_sentiment[]` | Per-ticker `{ticker, relevance_score, ticker_sentiment_score, ticker_sentiment_label}` |

**Sentiment label thresholds** (Alpha Vantage convention):

| Score range | Label |
|---|---|
| `≤ −0.35` | Bearish |
| `−0.35 to −0.15` | Somewhat-Bearish |
| `−0.15 to +0.15` | Neutral |
| `+0.15 to +0.35` | Somewhat-Bullish |
| `≥ +0.35` | Bullish |

## 2. Multi-ticker batched sentiment in 1 call

The endpoint accepts up to 100 tickers in a single call. Use this for watchlist-wide sentiment sweeps:

```bash
marketdata-cli news_sentiment --tickers AAPL,MSFT,NVDA,GOOGL,META --sort LATEST --limit 50
```

Each article returned includes a `ticker_sentiment[]` array with one entry per matching ticker — so you get per-ticker sentiment from each piece of news in one quota slot.

## 3. Topic-filtered sentiment

```bash
marketdata-cli news_sentiment --tickers AAPL --topics earnings --limit 20
```

Available topics:

| Topic value | Coverage |
|---|---|
| `earnings` | Earnings reports, guidance, surprises |
| `ipo` | IPOs and listings |
| `mergers_and_acquisitions` | M&A activity |
| `financial_markets` | General market commentary |
| `economy_macro` | Macro / GDP / employment |
| `economy_monetary` | Central banks, rates |
| `economy_fiscal` | Fiscal policy, taxes |
| `energy_transportation` | Energy, oil, transport |
| `finance` | Banking, financial services |
| `life_sciences` | Pharma, biotech, healthcare |
| `manufacturing` | Manufacturing |
| `real_estate` | REITs, housing |
| `retail_wholesale` | Retail |
| `technology` | Tech sector |

You can pass multiple topics comma-separated.

## 4. Time-windowed sentiment

Track sentiment around a specific event (earnings, fed meeting, etc.):

```bash
marketdata-cli news_sentiment \
  --tickers AAPL \
  --time_from 20260301T0000 \
  --time_to 20260331T2359 \
  --limit 100
```

## 5. Sentiment-driven workflow patterns

### Detect sentiment extremes (contrarian signal)

After fetching the feed, in `code-exec`:

```python
scores = [item["overall_sentiment_score"] for item in feed]
mean_sentiment = sum(scores) / len(scores)
# Flag as contrarian setup if |mean_sentiment| > 0.35 (extreme bullish or bearish)
```

A persistent extreme (>0.35 or <-0.35 sustained over 20+ articles) often precedes a reversal — surface this as a contrarian signal.

### Detect sentiment vs. price divergence

Pair the news sentiment fetch with a price pull and look for disagreement:

```bash
marketdata-cli news_sentiment            --tickers NVDA --limit 50
marketdata-cli time_series_daily_adjusted NVDA -o compact
```

In `code-exec`, compute the 5-day price change vs. the 5-day average sentiment score. Persistent price-up + sentiment-down (or vice versa) is a classic divergence setup.

### Compute sentiment momentum

Pull two windows and compare:

```bash
marketdata-cli news_sentiment --tickers AAPL --time_from 20260301T0000 --time_to 20260315T2359 --limit 100
marketdata-cli news_sentiment --tickers AAPL --time_from 20260316T0000 --time_to 20260331T2359 --limit 100
```

Mean sentiment in window 2 minus window 1 = sentiment momentum. Strongly positive momentum often leads price moves by a few days.

## 6. Earnings call sentiment (deep research)

For management commentary and tone shifts beyond press headlines, Alpha Vantage's `earnings_call_transcript` returns full transcripts with **LLM-tagged sentiment per speaker turn** — you get this nowhere else in the standard data ecosystem:

```bash
marketdata-cli earnings_call_transcript NVDA -q 2024Q4
marketdata-cli earnings_call_transcript NVDA -q 2024Q3   # for QoQ tone comparison
```

Use this when the user wants to understand guidance changes, management confidence, or red flags in CFO commentary.

## 7. Insider transactions (smart-money flow)

```bash
marketdata-cli insider_transactions AAPL
```

Recent insider buys are a strong positive signal; clustered insider sells in the months before an earnings report are a yellow flag.

## 8. Market-wide fear proxy

Alpha Vantage's free tier doesn't expose `^VIX` directly. Use VIX-tracking ETFs as proxies:

```bash
marketdata-cli time_series_daily_adjusted VIXY    # iPath VIX short-term futures ETF
marketdata-cli time_series_daily_adjusted UVXY    # ProShares VIX short-term (2x leveraged)
```

Spikes in VIXY correspond to market-wide fear; falling VIXY means complacency.

## What's not exposed (gracefully fall back)

These sentiment data points are not available from Alpha Vantage at any tier:

| Need | Alpha Vantage status |
|---|---|
| Analyst recommendation distribution / upgrades / downgrades | ❌ — only `AnalystTargetPrice` (single number) |
| Institutional ownership concentration / 13F | ❌ |
| Social-media sentiment (X / Reddit / StockTwits) | ❌ |
| Real Fear & Greed Index (CNN proprietary) | ❌ — use VIXY as a proxy |
| Put/call ratios | ❌ — requires options data (premium) |
| Fund flows (mutual fund / ETF) | ❌ |
| Short interest | ❌ |

When the user asks for any of these, surface "not available from Alpha Vantage" rather than fabricating.
