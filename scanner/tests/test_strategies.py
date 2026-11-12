import datetime as dt

from pms.betmath import FeeModel
from pms.config import load_config
from pms.strategies import arbitrage, favorites
from pms.track import update_ledger

NOW = dt.datetime(2026, 11, 12, 12, 0, tzinfo=dt.timezone.utc)
SERIES = {"KXGAME": {"category": "Sports", "fee_multiplier": 1}, "KXELEC": {"category": "Politics"}}


def market(ticker, event, yes_ask, yes_bid, hours=6, vol=5000, **kw):
    m = {
        "ticker": ticker, "event_ticker": event, "title": f"{ticker} wins", "yes_sub_title": ticker,
        "yes_ask_dollars": f"{yes_ask:.4f}", "yes_bid_dollars": f"{yes_bid:.4f}",
        "no_ask_dollars": f"{1 - yes_bid:.4f}", "no_bid_dollars": f"{1 - yes_ask:.4f}",
        "yes_ask_size_fp": "5000", "yes_bid_size_fp": "5000",
        "expected_expiration_time": (NOW + dt.timedelta(hours=hours)).isoformat(),
        "close_time": (NOW + dt.timedelta(days=14)).isoformat(),
        "volume_24h_fp": str(vol), "volume_fp": str(vol * 3), "rules_primary": "",
    }
    m.update(kw)
    return m


def test_favorites_picks_yes_and_no_sides():
    cfg = load_config()
    ms = [market("KXGAME-A-HOME", "KXGAME-A", 0.93, 0.92),   # YES at 93c qualifies
          market("KXGAME-B-AWAY", "KXGAME-B", 0.09, 0.08)]   # NO costs 92c, qualifies
    out = favorites(ms, SERIES, cfg, FeeModel(), 100, NOW)
    ids = {o["id"] for o in out}
    assert ids == {"fav:KXGAME-A-HOME:yes", "fav:KXGAME-B-AWAY:no"}
    no = next(o for o in out if o["side"] == "no")
    assert no["price"] == 0.92 and no["outcome"] == "NOT KXGAME-B-AWAY"
    assert no["category"] == "Sports"


def test_favorites_filters_illiquid_wide_and_far():
    cfg = load_config()
    ms = [market("KXGAME-C-X", "KXGAME-C", 0.93, 0.92, vol=10),            # dead market
          market("KXGAME-D-X", "KXGAME-D", 0.94, 0.50),                    # wide spread
          market("KXGAME-E-X", "KXGAME-E", 0.93, 0.92, hours=24 * 30),     # too far out
          market("KXGAME-F-X", "KXGAME-F", 0.99, 0.98)]                    # too expensive
    assert favorites(ms, SERIES, cfg, FeeModel(), 100, NOW) == []


def test_favorites_caps_per_event():
    cfg = load_config()
    ms = [market(f"KXGAME-G-P{i}", "KXGAME-G", 0.07, 0.06) for i in range(6)]  # NO on 6 longshots
    out = favorites(ms, SERIES, cfg, FeeModel(), 100, NOW)
    assert len(out) == cfg["favorites"]["max_per_event"]


def test_arbitrage_requires_mutually_exclusive_event():
    cfg = load_config()
    ms = [market("KXELEC-X-A", "KXELEC-X", 0.40, 0.39, vol=100),
          market("KXELEC-X-B", "KXELEC-X", 0.45, 0.44, vol=100)]
    found = arbitrage(ms, SERIES, cfg, FeeModel(), 100, NOW, fetch_event=lambda e: {"mutually_exclusive": True})
    assert len(found) == 1 and found[0]["bet"]["profit"] > 0 and len(found[0]["legs"]) == 2
    rejected = arbitrage(ms, SERIES, cfg, FeeModel(), 100, NOW, fetch_event=lambda e: {"mutually_exclusive": False})
    assert rejected == []


class FakeClient:
    def __init__(self, results):
        self.results = results

    def markets_by_ticker(self, tickers):
        return [{"ticker": t, "result": self.results.get(t, ""), "status": "finalized"} for t in tickers]


def test_ledger_records_and_resolves():
    cfg = load_config()
    ms = [market("KXGAME-A-HOME", "KXGAME-A", 0.93, 0.92, hours=1),
          market("KXGAME-B-AWAY", "KXGAME-B", 0.09, 0.08, hours=1)]
    scan = {"opportunities": favorites(ms, SERIES, cfg, FeeModel(), 100, NOW)}
    ledger = update_ledger(None, scan, now=NOW)
    assert ledger["summary"]["tracked"] == 2 and ledger["summary"]["resolved"] == 0

    later = NOW + dt.timedelta(hours=3)
    client = FakeClient({"KXGAME-A-HOME": "yes", "KXGAME-B-AWAY": "yes"})  # A wins (we win), B-away wins (we lose)
    ledger = update_ledger(ledger, {"opportunities": []}, client, now=later)
    s = ledger["summary"]
    assert s["resolved"] == 2 and s["wins"] == 1
    a = ledger["picks"]["fav:KXGAME-A-HOME:yes"]["result"]
    b = ledger["picks"]["fav:KXGAME-B-AWAY:no"]["result"]
    assert a["won"] and a["profit"] > 0
    assert not b["won"] and b["profit"] == -b["staked"]
