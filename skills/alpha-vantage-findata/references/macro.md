# Macro & Market Overview

**Goal:** Understand the economic backdrop and overall market conditions.

Each call costs 1 of your 25 daily Alpha Vantage requests.

## 1. Economic health

GDP growth, inflation, and employment:

```bash
marketdata-cli real_gdp
marketdata-cli real_gdp_per_capita
marketdata-cli cpi
marketdata-cli inflation
marketdata-cli unemployment
marketdata-cli nonfarm_payroll
```

## 2. Monetary policy

Rates and yields:

```bash
marketdata-cli federal_funds_rate
marketdata-cli treasury_yield
```

## 3. Consumer & business activity

```bash
marketdata-cli retail_sales
marketdata-cli durables
```

## 4. Commodities

```bash
marketdata-cli wti
marketdata-cli brent
marketdata-cli natural_gas
marketdata-cli gold_silver_spot
marketdata-cli copper
marketdata-cli aluminum
marketdata-cli wheat
marketdata-cli corn
marketdata-cli cotton
marketdata-cli sugar
marketdata-cli coffee
```

## 5. Market movers & status

Today's biggest gainers/losers and exchange hours:

```bash
marketdata-cli top_gainers_losers
marketdata-cli market_status
```

## 6. Upcoming events

Earnings and IPO calendars:

```bash
marketdata-cli earnings_calendar
marketdata-cli ipo_calendar
```

## 7. Listing status

Active or delisted US stocks and ETFs:

```bash
marketdata-cli listing_status
```
