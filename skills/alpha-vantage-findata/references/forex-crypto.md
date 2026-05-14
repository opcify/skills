# Forex & Crypto

**Goal:** Check exchange rates and price history for currencies and cryptocurrencies.

Each call costs 1 of your 25 daily Alpha Vantage requests, subject to the same 5/min rate limit.

## Forex

### Spot exchange rate

```bash
marketdata-cli currency_exchange_rate --from_currency USD --to_currency JPY
```

### Daily history

```bash
marketdata-cli fx_daily --from_symbol EUR --to_symbol USD
```

Note the flag difference: spot uses `--from_currency` / `--to_currency`, time series uses `--from_symbol` / `--to_symbol`.

### Intraday

```bash
marketdata-cli fx_intraday --from_symbol EUR --to_symbol USD -i 5min
```

Supported intervals: `1min`, `5min`, `15min`, `30min`, `60min`.

### Weekly / monthly

```bash
marketdata-cli fx_weekly  --from_symbol EUR --to_symbol USD
marketdata-cli fx_monthly --from_symbol EUR --to_symbol USD
```

## Crypto

### Daily history

```bash
marketdata-cli digital_currency_daily --symbol BTC --market USD
```

### Weekly / monthly

```bash
marketdata-cli digital_currency_weekly  --symbol BTC --market USD
marketdata-cli digital_currency_monthly --symbol BTC --market USD
```

### Intraday

```bash
marketdata-cli crypto_intraday --symbol ETH --market USD -i 5min
```
