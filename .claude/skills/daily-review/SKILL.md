---
name: daily-review
description: Claude's twice-daily review of the scanner's picks. Reads the latest scan, researches the best candidates, labels each Strong / Reasonable / Pass with its own win-chance estimate, and publishes opinions.json to the data branch so the dashboard shows "Claude's take". Run by the scheduled routine; also on request ("review the picks").
---

# Daily review

You are giving a careful second opinion, not cheerleading. Most picks are priced fairly; a good review says
"Pass" often. Never place trades. Times are shown to the user in US Eastern (ET).

## 1. Get the latest scan
```bash
cd <repo root>
git fetch origin data
git show origin/data:latest.json > /tmp/latest.json
git show origin/data:picks.json > /tmp/picks.json 2>/dev/null || true
```
If `latest.json` is older than 3 hours (`generated_at`), run a fresh scan instead:
`cd scanner && python -m pms.scan --out /tmp/scan` and use `/tmp/scan/latest.json`.

## 2. Choose what to review (about 15 picks, at most 20)
From `opportunities`, skip `in_progress` picks (prices move too fast to review usefully). Prefer, in order:
- all `arbitrage` picks;
- picks settling within the next ~14 hours (before the next review), highest `score` first;
- then the highest-`score` picks settling later.
Spread across categories: no more than 8 from one category.

## 3. Check each pick
For each one:
1. **Re-check the price** (prices may have moved since the scan):
   `curl -s "https://api.elections.kalshi.com/trade-api/v2/markets/<ticker>"` and read the ask for the pick's
   side (`yes_ask_dollars`, or `no_ask_dollars` for NO). Note it as `price_at_review`. If it's now outside
   85–97¢ or the market is closed, mark it Pass with the reason.
2. **Read the rules** (`rules` in the pick, `rules_secondary` from the API): what exactly settles it, ties,
   cancellations, data source, timing. Settlement wording is the most common hidden risk.
3. **Research** with web search, matched to the category:
   - Sports: injuries, lineups, rest, motivation, weather for outdoor games, line moves at sportsbooks.
     For props ("25+ points") check recent minutes and averages.
   - Crypto / commodities / indexes with a strike: the current price versus the strike and how far it
     typically moves in the remaining time.
   - Economics: the consensus forecast and recent surprises for that release.
   - Weather: the latest forecast for the station named in the rules.
   - Politics / entertainment / other: the latest reliable reporting.
4. **Estimate your own win chance** (`claude_prob`, 0–1). Be calibrated: if you have no information beyond
   the price, use the market's price.
5. **Verdict**:
   - `strong`: your chance is at least ~3 points above the price **and** no serious red flags.
   - `reasonable`: roughly agrees with the price and no serious red flags; fair bet, little edge.
   - `pass`: your chance is at or below the break-even chance (`bet.breakeven_prob`), a serious red flag,
     unclear rules, or you couldn't verify enough.
6. Write a **reason** of 1–3 plain sentences a non-expert can follow, citing what you found. List
   **red_flags** as short phrases.

## 4. Publish
Write `opinions.json` in this exact shape:
```json
{
  "generated_at": "<UTC ISO time>",
  "summary": "2–4 plain sentences: how many reviewed, the best one or two and why, anything to avoid.",
  "picks": {
    "<opportunity id, e.g. fav:KXNBAGAME-...:yes>": {
      "verdict": "strong | reasonable | pass",
      "claude_prob": 0.94,
      "reason": "…",
      "red_flags": ["…"],
      "price_at_review": 0.91
    }
  }
}
```
Keys must be the pick's `id` from latest.json exactly. Then commit it to the `data` branch:
```bash
git worktree add -B data /tmp/data-branch origin/data 2>/dev/null || (cd /tmp/data-branch && git pull -q origin data)
cp opinions.json /tmp/data-branch/opinions.json
cd /tmp/data-branch
git add opinions.json
git commit -m "Claude review $(TZ=America/New_York date '+%Y-%m-%d %H:%M ET')"
for i in 1 2 3; do git push origin data && break; git pull --rebase origin data; done
```
Then ask GitHub to rebuild the dashboard now (otherwise the next half-hourly scan picks it up):
`gh api -X POST repos/apancerella/prediction-market-scanner/actions/workflows/scan.yml/dispatches -f ref=main`
(if that's refused, that's fine; say the dashboard updates within 30 minutes).

## 5. Update the Claude artifact
Follow the `publish-artifact` skill to republish the dashboard (with your new opinions) to the user's
Claude artifact.

## 6. Finish
End with a short summary: picks reviewed, Strong picks (outcome, price, $100 profit if it wins, why), and
anything notable to avoid. Notifications are off by default: don't send any unless this session's prompt
says to.
