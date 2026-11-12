---
name: kalshi-api
description: Field notes for Kalshi's public market-data API that this scanner reads (endpoints, pagination, rate limits, price fields, settlement fields). Read before changing scanner/pms/kalshi.py or any code that reads market fields.
---

# Kalshi public API notes

Base URL: `https://api.elections.kalshi.com/trade-api/v2` (serves all categories despite the name). No auth for
market data. Robinhood's prediction markets are Kalshi event contracts; Robinhood lists a subset.

## Endpoints used
| Call | Use |
|---|---|
| `GET /markets?status=open&limit=1000&mve_filter=exclude&max_close_ts=<unix>&cursor=` | all open plain binary markets; ~75–100k rows, ~75–100 pages |
| `GET /series` | one call, ~16k series: `category`, `tags`, `fee_type`, `fee_multiplier` |
| `GET /events/{event_ticker}` | `event.mutually_exclusive` (needed before calling anything arbitrage) |
| `GET /markets?tickers=A,B,C` | batch lookup, used to read `result` once picks settle |

Pagination: pass back `cursor` until it's empty. `mve_filter=exclude` drops combo/parlay markets.

## Rate limits
Bursts return **HTTP 429** quickly. `KalshiClient.get` retries with backoff; keep `pause` ≥ 0.2s between pages.

## Fields (strings, in dollars or contract counts)
- Prices: `yes_ask_dollars`, `yes_bid_dollars`, `no_ask_dollars`, `no_bid_dollars`, `last_price_dollars`. Parse
  with `float()`. NO ask = 1 − YES bid.
- Size at top of book: `yes_ask_size_fp`, `yes_bid_size_fp` (NO ask depth = YES bid size).
- Volume: `volume_24h_fp`, `volume_fp`, `open_interest_fp`.
- Time: `expected_expiration_time` (when it should settle; may be in the past for live games), `close_time`
  (often weeks after a game), `latest_expiration_time`.
- Text: `title`, `yes_sub_title` (the YES outcome), `no_sub_title` (usually the same text, not the inverse),
  `rules_primary`, `rules_secondary` (tie/cancel rules, often "resolve to $0.50").
- Result: `result` is `"yes"`/`"no"` once settled, `""` before; `status` becomes `finalized`.
- Series ticker = event ticker up to the first `-`. Kalshi web URL: `https://kalshi.com/markets/<series lower>`.

## Gotchas
- Many markets show a 90¢+ ask with zero volume: always filter on volume and spread.
- Multi-outcome events are not always mutually exclusive or exhaustive; check before treating as arbitrage.
- Field names have changed before (cents ints → `_dollars` strings). If parsing breaks, fetch one market with
  `curl -s "$BASE/markets?limit=1&status=open"` and compare.
