---
name: track-record
description: Report how the scanner's past picks actually turned out (win rate, profit on $100 per pick, by type, price band and category). Use when the user asks whether the picks work, how Claude's verdicts have done, or before trusting a strategy with real money.
---

# Track record

1. Load the ledger: `git fetch origin data && git show origin/data:picks.json > /tmp/picks.json`.
   Each pick has `first_price`, `first_bet` (the $100 bet when first seen), `category`, `strategy`, and
   `result` (`won`, `profit`, `staked`) once settled. `summary` has totals; `archived` holds totals for picks
   older than 120 days.
2. Report, with Python on the JSON:
   - overall: settled count, win rate, total profit, ROI;
   - by price band (85–89¢, 90–94¢, 95–97¢): **compare win rate to the average price**. If 92¢ picks win
     about 92% of the time, the market is priced fairly and the strategy loses about the fees;
   - by category and by strategy;
   - the biggest losses (what went wrong).
3. If `opinions.json` history exists in `git log origin/data -- opinions.json`, compare verdicts with outcomes
   (Strong vs Pass win rates). Check out older versions with `git show <sha>:opinions.json`.
4. Be blunt about sample size: under ~100 settled picks per band, say the numbers are noise.
5. Never imply a guaranteed profit.
