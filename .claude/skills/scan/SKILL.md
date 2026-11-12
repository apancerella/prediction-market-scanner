---
name: scan
description: Run the prediction-market scanner on demand and summarize the top "easy win" picks with their $100 payout. Use when the user asks what's good right now, wants a quick scan, or wants to check how many picks qualify after changing config.toml.
---

# Scan

1. From the repo root run:
   ```bash
   cd scanner && python -m pms.scan --dry-run --top 20
   ```
   A full scan reads ~100k markets and takes about 2 minutes (Kalshi rate-limits; the client retries on 429).
   To also write files for the local dashboard, drop `--dry-run` (writes `web/public/data/`).
2. If the host `api.elections.kalshi.com` is blocked, say so; don't invent prices.
3. Report a short table: outcome, market's chance, price, settles in (ET), profit if it wins, loss if it loses.
   Always show the loss next to the profit. Mention any flags (thin order book, live event, tie rule).
4. Remind the user to confirm the market is listed in the Robinhood app; Robinhood lists a subset of Kalshi markets.

Optional: `git fetch origin data && git show origin/data:latest.json` shows the most recent scheduled scan
without hitting the API.
