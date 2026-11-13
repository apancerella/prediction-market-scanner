# Prediction Market Scanner

Scans the prediction markets behind Robinhood's event contracts for high-probability "easy win" candidates,
shows what a **$100 bet** on each would win (and lose), and gets a **twice-daily second opinion from Claude**.

> **Not financial advice.** A 95¢ contract wins about $4 on $100 and loses about $100 when it misses.
> These picks are what the market already expects; they only make money if the real chance is better than the price.

## What it does
- **Scans every 30 minutes** (GitHub Actions) all open Kalshi markets, the exchange Robinhood's prediction markets use.
- **Finds two kinds of opportunities**
  - *Favorites*: contracts priced 85–97¢ that settle within 7 days, with real trading volume and a tight spread.
  - *Arbitrage*: mutually exclusive events where buying every outcome costs less than $1 after fees (rare).
- **Estimates a $100 bet**: contracts bought, fees (Robinhood ~1¢ + ~1¢ per contract), profit if it wins,
  loss if it loses, and the break-even win chance.
- **Tracks results**: remembers every pick and scores it when the market settles, so you can see whether the
  "easy wins" actually win.
- **Claude's take**: around 8:45 AM and 5:45 PM ET a scheduled Claude Code session researches the top picks
  (news, injuries, data releases, settlement rules) and labels each Strong / Reasonable / Pass. No
  notifications: check the dashboard when you want.

## Dashboard
- GitHub Pages (updates every scan): `https://apancerella.github.io/prediction-market-scanner/`
- Claude artifact (updates after each Claude review, twice a day): private to your Claude account.

## Tuning
Edit [`config.toml`](config.toml) (minimum price, days to settle, liquidity, fees, categories). Push to `main`
and the next scan uses it.

## Run locally
```bash
cd scanner && python -m pms.scan          # needs Python 3.11+, no packages
cd web && npm install && npm run dev
```
Tests: `cd scanner && pip install pytest && python -m pytest -q`

## Caveats
- Robinhood has no public API for event contracts, so prices come from Kalshi. Robinhood lists a subset of
  these markets and its quotes can differ slightly. Confirm in the app.
- The order book's top level may not hold a full $100 order; such picks are flagged.
- Claude's opinion is research-backed but can be wrong.
