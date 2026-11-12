"""Pick ledger: remembers every opportunity the scanner has shown and how it turned out.

This is how we find out whether "easy wins" actually win. Each pick is recorded the
first time it appears, its price is sampled on every scan (for the chart), and once
the market settles we record the result and the profit or loss on the stake.
"""

from __future__ import annotations

import datetime as dt

MAX_SAMPLES = 96          # price points kept per pick
KEEP_RESOLVED_DAYS = 120  # older resolved picks are dropped (summary keeps the totals)


def _now_iso(now: dt.datetime) -> str:
    return now.replace(microsecond=0).isoformat()


def new_ledger() -> dict:
    return {"picks": {}, "archived": {"count": 0, "wins": 0, "profit": 0.0, "staked": 0.0}, "summary": {}}


def update_ledger(ledger: dict | None, scan: dict, client=None, now: dt.datetime | None = None) -> dict:
    ledger = ledger or new_ledger()
    now = now or dt.datetime.now(dt.timezone.utc)
    stamp = _now_iso(now)
    picks = ledger["picks"]
    for o in scan["opportunities"]:
        p = picks.get(o["id"])
        if p is None:
            p = picks[o["id"]] = {
                "id": o["id"], "strategy": o["strategy"], "ticker": o["ticker"], "side": o["side"],
                "legs": [leg["ticker"] for leg in o.get("legs", [])],
                "title": o["title"], "outcome": o["outcome"], "category": o["category"],
                "url": o["url"], "first_seen": stamp, "first_price": o["price"],
                "first_bet": o["bet"], "settles_at": o["settles_at"], "samples": [], "result": None,
            }
        p["last_seen"] = stamp
        p["last_price"] = o["price"]
        p["settles_at"] = o["settles_at"]
        p["samples"].append([stamp, o["price"]])
        del p["samples"][:-MAX_SAMPLES]
    if client is not None:
        resolve(ledger, client, now)
    prune(ledger, now)
    ledger["summary"] = summarize(ledger)
    ledger["updated_at"] = stamp
    return ledger


def _due(p: dict, now: dt.datetime) -> bool:
    if p["result"] is not None or not p.get("settles_at"):
        return False
    return dt.datetime.fromisoformat(p["settles_at"]) < now


def resolve(ledger: dict, client, now: dt.datetime) -> None:
    """Look up settled markets and record win/loss using the bet from when the pick first appeared."""
    due = [p for p in ledger["picks"].values() if _due(p, now)]
    tickers = sorted({t for p in due for t in (p["legs"] or [p["ticker"]])})
    if not tickers:
        return
    results = {m["ticker"]: (m.get("result") or "", m.get("status")) for m in client.markets_by_ticker(tickers)}
    for p in due:
        if p["legs"]:  # arbitrage: one leg must have resolved yes
            res = [results.get(t, ("", None))[0] for t in p["legs"]]
            if any(r == "" for r in res):
                continue
            won = any(r == "yes" for r in res)
        else:
            r = results.get(p["ticker"], ("", None))[0]
            if r not in ("yes", "no"):
                continue  # not settled yet (or a void/scalar result we don't score)
            won = r == p["side"]
        b = p["first_bet"]
        p["result"] = {"won": won, "settled_seen": _now_iso(now),
                       "profit": b["profit"] if won else -b["total_cost"], "staked": b["total_cost"]}


def prune(ledger: dict, now: dt.datetime) -> None:
    cutoff = now - dt.timedelta(days=KEEP_RESOLVED_DAYS)
    arch = ledger["archived"]
    for pid in list(ledger["picks"]):
        p = ledger["picks"][pid]
        stale_unresolved = p["result"] is None and dt.datetime.fromisoformat(p["last_seen"]) < cutoff
        if p["result"] and dt.datetime.fromisoformat(p["result"]["settled_seen"]) < cutoff:
            arch["count"] += 1
            arch["wins"] += int(p["result"]["won"])
            arch["profit"] = round(arch["profit"] + p["result"]["profit"], 2)
            arch["staked"] = round(arch["staked"] + p["result"]["staked"], 2)
            del ledger["picks"][pid]
        elif stale_unresolved:
            del ledger["picks"][pid]


def summarize(ledger: dict) -> dict:
    arch = ledger["archived"]
    resolved = [p for p in ledger["picks"].values() if p["result"]]
    by_strategy: dict[str, dict] = {}
    for p in resolved:
        s = by_strategy.setdefault(p["strategy"], {"resolved": 0, "wins": 0, "profit": 0.0, "staked": 0.0})
        s["resolved"] += 1
        s["wins"] += int(p["result"]["won"])
        s["profit"] = round(s["profit"] + p["result"]["profit"], 2)
        s["staked"] = round(s["staked"] + p["result"]["staked"], 2)
    n = len(resolved) + arch["count"]
    wins = sum(int(p["result"]["won"]) for p in resolved) + arch["wins"]
    profit = round(sum(p["result"]["profit"] for p in resolved) + arch["profit"], 2)
    staked = round(sum(p["result"]["staked"] for p in resolved) + arch["staked"], 2)
    return {
        "tracked": len(ledger["picks"]), "resolved": n, "wins": wins,
        "win_rate": round(wins / n, 4) if n else None,
        "profit": profit, "staked": staked,
        "roi_pct": round(profit / staked * 100, 2) if staked else None,
        "by_strategy": by_strategy,
    }
