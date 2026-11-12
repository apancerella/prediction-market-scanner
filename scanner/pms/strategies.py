"""Detectors for "easy win" opportunities. Each returns a list of Opportunity dicts.

To add one, follow .claude/skills/add-strategy/SKILL.md.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Callable

from .betmath import FeeModel, bet
from .kalshi import market_url, series_ticker


def _f(x) -> float:
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def _ts(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def settle_time(m: dict) -> dt.datetime | None:
    """When the market is expected to settle (falls back to its close time)."""
    return _ts(m.get("expected_expiration_time")) or _ts(m.get("close_time"))


def days_until(t: dt.datetime | None, now: dt.datetime) -> float | None:
    return None if t is None else (t - now).total_seconds() / 86400


def risk_label(prob: float) -> str:
    if prob >= 0.95:
        return "Low payout, low implied risk"
    if prob >= 0.90:
        return "Favorite"
    return "Moderate favorite"


def _base(m: dict, series: dict, now: dt.datetime) -> dict:
    st = settle_time(m)
    ser = series.get(series_ticker(m["event_ticker"]), {})
    return {
        "ticker": m["ticker"],
        "event_ticker": m["event_ticker"],
        "series_ticker": series_ticker(m["event_ticker"]),
        "category": ser.get("category") or "Other",
        "tags": ser.get("tags") or [],
        "title": m.get("title") or "",
        "settles_at": st.isoformat() if st else None,
        "close_time": m.get("close_time"),
        "days_to_settle": None if st is None else round(max(days_until(st, now), 0.0), 3),
        "in_progress": bool(st and st < now),
        "volume_24h": _f(m.get("volume_24h_fp")),
        "volume_total": _f(m.get("volume_fp")),
        "open_interest": _f(m.get("open_interest_fp")),
        "rules": (m.get("rules_primary") or "")[:600],
        "url": market_url(m["event_ticker"]),
    }


def favorites(markets: list[dict], series: dict, cfg: dict, fee_model: FeeModel, stake: float,
              now: dt.datetime) -> list[dict]:
    """Contracts the market prices as very likely (e.g. 85–97¢), settling soon, with real liquidity."""
    c = cfg["favorites"]
    out = []
    for m in markets:
        st = settle_time(m)
        days = days_until(st, now)
        if days is None or days > c["max_days_to_settle"]:
            continue
        if _f(m.get("volume_24h_fp")) < c["min_volume_24h"]:
            continue
        mult = _f(series.get(series_ticker(m["event_ticker"]), {}).get("fee_multiplier")) or 1.0
        for side in ("yes", "no"):
            ask = _f(m.get(f"{side}_ask_dollars"))
            bid = _f(m.get(f"{side}_bid_dollars"))
            if not (c["min_price"] <= ask <= c["max_price"]) or bid <= 0:
                continue
            spread = round(ask - bid, 4)
            if spread > c["max_spread"]:
                continue
            b = bet(ask, stake, fee_model, days=max(days, 0.0), multiplier=mult)
            if b.contracts == 0 or b.profit < c["min_profit"]:
                continue
            flags = []
            # Top-of-book depth is only published for YES asks; NO asks mirror YES bids.
            depth = _f(m.get("yes_ask_size_fp")) if side == "yes" else _f(m.get("yes_bid_size_fp"))
            if depth and depth < b.contracts:
                flags.append(f"Only {int(depth)} contracts at this price; a $100 order may fill higher")
            if st and st < now:
                flags.append("Event already under way: price can swing fast")
            if "tie" in (m.get("rules_secondary") or "").lower() and "0.50" in (m.get("rules_secondary") or ""):
                flags.append("A tie or cancellation settles at 50¢ (you'd lose about half)")
            subj = m.get("yes_sub_title") or m.get("title")
            outcome = subj if side == "yes" else f"NOT {subj}"
            o = _base(m, series, now)
            o.update({
                "id": f"fav:{m['ticker']}:{side}",
                "strategy": "favorite",
                "side": side,
                "outcome": outcome,
                "price": ask,
                "bid": bid,
                "spread": spread,
                "implied_prob": ask,
                "risk": risk_label(ask),
                "flags": flags,
                "bet": b.to_dict(),
            })
            out.append(o)
    # Cap picks per event, keeping the highest-ranked.
    out.sort(key=score, reverse=True)
    per_event: dict[str, int] = defaultdict(int)
    kept = []
    for o in out:
        if per_event[o["event_ticker"]] >= c["max_per_event"]:
            continue
        per_event[o["event_ticker"]] += 1
        kept.append(o)
    return kept


def arbitrage(markets: list[dict], series: dict, cfg: dict, fee_model: FeeModel, stake: float,
              now: dt.datetime, fetch_event: Callable[[str], dict] | None = None) -> list[dict]:
    """Events where buying YES on every outcome costs less than the $1 one of them must pay."""
    c = cfg["arbitrage"]
    by_event: dict[str, list[dict]] = defaultdict(list)
    for m in markets:
        by_event[m["event_ticker"]].append(m)
    out = []
    for ev, legs in by_event.items():
        if len(legs) < 2:
            continue
        asks = [_f(m.get("yes_ask_dollars")) for m in legs]
        if any(a <= 0 for a in asks) or sum(asks) >= 1:
            continue
        st = max((settle_time(m) for m in legs if settle_time(m)), default=None)
        days = days_until(st, now)
        if days is None or days > c["max_days_to_settle"]:
            continue
        if any(_f(m.get("volume_24h_fp")) < c["min_volume_24h"] for m in legs):
            continue
        mult = _f(series.get(series_ticker(ev), {}).get("fee_multiplier")) or 1.0
        b = bet(0, stake, fee_model, days=max(days, 0.0), multiplier=mult, leg_prices=asks)
        if b.contracts == 0 or b.profit < c["min_profit"]:
            continue
        # Only a true arbitrage if exactly one outcome must win. Confirm with the event record.
        if fetch_event is not None:
            info = fetch_event(ev)
            if not info.get("mutually_exclusive"):
                continue
        o = _base(legs[0], series, now)
        o.update({
            "id": f"arb:{ev}",
            "strategy": "arbitrage",
            "ticker": ev,
            "side": "yes",
            "title": legs[0].get("title") or ev,
            "outcome": f"Buy YES on all {len(legs)} outcomes",
            "legs": [{"ticker": m["ticker"], "outcome": m.get("yes_sub_title"), "price": a}
                     for m, a in zip(legs, asks)],
            "price": round(sum(asks), 4),
            "bid": None,
            "spread": None,
            "implied_prob": 1.0,
            "risk": "Arbitrage (verify every outcome is listed)",
            "flags": ["Check that the listed outcomes cover every possibility; "
                      "if none of them happens you lose the whole stake"],
            "volume_24h": min(_f(m.get("volume_24h_fp")) for m in legs),
            "settles_at": st.isoformat() if st else None,
            "days_to_settle": round(max(days, 0.0), 3),
            "bet": b.to_dict(),
        })
        out.append(o)
    return out


def score(o: dict) -> float:
    """Default ranking for "easy wins": most likely first, then sooner, then more liquid.

    Points = implied win chance in % (dominant), minus 0.15 per day to settle (max 7 days),
    plus up to 0.5 for liquidity. Arbitrage counts as 100% likely.
    """
    days = min(o.get("days_to_settle") or 0.0, 7.0)
    liquidity = min(o.get("volume_24h", 0) / 20_000, 1.0)
    return o["implied_prob"] * 100 - 0.15 * days + 0.5 * liquidity


STRATEGIES = {
    "favorites": favorites,
    "arbitrage": arbitrage,
}
