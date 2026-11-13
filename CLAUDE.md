# Prediction Market Scanner

Finds "easy win" candidates in the prediction markets Robinhood offers (Kalshi event contracts), estimates
the result of a $100 bet on each, shows them on a web dashboard, and gets a twice-daily second opinion from
Claude. It never places trades.

## Layout
- `config.toml`: thresholds for what counts as an easy win, the stake, the fee model. User-facing; keep comments plain.
- `scanner/pms/`: Python 3.11+, standard library only.
  - `kalshi.py`: read-only client for Kalshi's public API (retries on 429).
  - `betmath.py`: **all** money math (contracts, fees, payout, break-even, EV). Nothing else computes money.
  - `strategies.py`: detectors (`favorites`, `arbitrage`) plus `score` (default ranking: most likely first).
  - `track.py`: pick ledger (`picks.json`): first-seen bet, price samples, settled results, track record.
  - `scan.py`: CLI entry point; writes `latest.json` and `picks.json`.
- `scanner/tests/`: pytest. Run `cd scanner && python -m pytest -q`.
- `web/`: React + Vite + TypeScript dashboard. Reads `data/latest.json`, `data/picks.json`, `data/opinions.json`.
- `.github/workflows/scan.yml`: every 30 min: tests → scan → commit JSON to the `data` branch → build → GitHub Pages.

## Data flow
`main` holds code only. Generated JSON lives on the orphan **`data` branch** (`latest.json`, `picks.json`,
`opinions.json`), so scans don't clutter history. The workflow copies those files into the built site.
The daily review (`opinions.json`) is written by a scheduled Claude Code session at about 8:45 AM and
5:45 PM ET using the `daily-review` skill, which then republishes the dashboard as a Claude artifact
(https://claude.ai/artifact/YQzrDcWQSEPMtHqzxsHk35) with the `publish-artifact` skill. The artifact is a
snapshot: `web/scripts/build-artifact.mjs` inlines the built app and the data into one page, because
artifacts can't fetch from other sites.

## Commands
```bash
cd scanner && python -m pms.scan --dry-run        # quick look, writes nothing
cd scanner && python -m pms.scan                  # writes web/public/data/ for local dev
cd web && npm install && npm run dev              # dashboard at http://localhost:5173
cd web && npm run build                           # type-check + production build
```

## Rules
- Show the loss next to every profit. Never call a pick guaranteed or risk-free.
- Use the **ask** price for the side being bought, never bid or last trade.
- Prices are Kalshi's; Robinhood may not list every market. Say so wherever picks are presented.
- Don't add trading or order-placing code.
- Keep the scanner dependency-free (stdlib) so the Action stays fast and reliable.

## Skills
`scan`, `bet-math`, `kalshi-api`, `add-strategy`, `track-record`, `daily-review`, `publish-artifact` in `.claude/skills/`.
