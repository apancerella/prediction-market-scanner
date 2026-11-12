---
name: add-strategy
description: Step-by-step guide for adding a new kind of "easy win" detector to the scanner (code, config, tests, ledger, dashboard). Use when the user asks to look for a new type of opportunity.
---

# Add a strategy

1. **Write the detector** in `scanner/pms/strategies.py` with the same signature as `favorites`:
   `(markets, series, cfg, fee_model, stake, now) -> list[dict]`. Build each item from `_base(...)` and add:
   `id` (stable, prefixed, e.g. `"xyz:<ticker>:<side>"`), `strategy`, `side`, `outcome` (plain English: what
   you're betting on), `price` (ask), `bid`, `spread`, `implied_prob`, `risk` (short label), `flags`
   (plain-English warnings), and `bet` from `betmath.bet(...)`. Never compute money outside betmath.
2. **Add a config section** in `config.toml` and defaults in `scanner/pms/config.py`, with comments a
   non-programmer can follow. Include `enabled`.
3. **Wire it up** in `run_scan` in `scanner/pms/scan.py`.
4. **Ledger**: if the pick isn't a single YES/NO contract, teach `track.resolve` how to score it.
5. **Tests**: add fixtures to `scanner/tests/test_strategies.py`: one that qualifies, one per filter that
   should reject. Run `cd scanner && python -m pytest -q`.
6. **Dashboard**: add the type to the "All types" select and `Opportunity["strategy"]` in `web/src/types.ts`,
   explain it in the "How it works" tab, and run `cd web && npm run build`.
7. **Daily review**: if Claude needs different research for it, update `.claude/skills/daily-review/SKILL.md`.
8. Run a real `--dry-run` scan and check the new picks by eye before committing.
