---
name: bet-math
description: The rules for every dollar figure in this project (contracts, fees, payout, profit, return, break-even, expected value). Read before changing scanner/pms/betmath.py, the fee settings in config.toml, or any UI that displays money.
---

# Bet math

All money math lives in `scanner/pms/betmath.py`. Nothing else computes payouts; the web app only displays
what the scanner wrote. Keep it that way.

## Rules
- A contract costs its **ask** price (what you'd pay now, never the bid or last trade) and pays **$1.00** if it
  wins, **$0** if it loses.
- **Contracts** = the largest whole number where `contracts × price + fees ≤ stake`. Never exceed the stake.
- **Fees** (`[fees]` in config.toml):
  - `robinhood` (default): commission + exchange fee per contract, $0.01 + $0.01.
  - `kalshi`: `ceil_to_cent(0.07 × fee_multiplier × contracts × P × (1 − P))`, the quadratic taker fee.
- **Total cost** = cost + fees. **Max loss** = total cost (you lose everything you spent).
- **Payout** = contracts × $1. **Profit** = payout − total cost. **Return %** = profit ÷ total cost.
- **Break-even chance** = total cost ÷ payout. Show it: it's the real hurdle after fees.
- **Annualized** compounds over 365 days with days floored at 1, and is hidden when absurd (>1,000,000%).
- **Expected value** at a win chance p = p × payout − total cost. At the market's own price EV ≈ −fees; a pick
  only has an edge if the true chance beats the break-even chance.
- **Arbitrage bundles**: buy the same number of YES contracts on every leg; one bundle pays $1. Fees are per leg.

## When changing it
1. Update `betmath.py` and `scanner/tests/test_betmath.py` together. Hand-check one example in the test.
2. Run `cd scanner && python -m pytest -q`.
3. If the JSON shape of `bet` changes, update `web/src/types.ts` and the card in `web/src/App.tsx`.
4. Never show profit without the loss next to it.
