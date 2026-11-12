"""Minimal read-only client for Kalshi's public market-data API (no login needed).

Robinhood's prediction markets are event contracts listed on Kalshi, so Kalshi's
order book is the best public source for the prices Robinhood shows.
See .claude/skills/kalshi-api/SKILL.md for field notes.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
USER_AGENT = "prediction-market-scanner/0.1"


class KalshiClient:
    def __init__(self, base_url: str = BASE_URL, pause: float = 0.25, retries: int = 8, timeout: float = 60):
        self.base_url = base_url
        self.pause = pause          # polite gap between paginated calls
        self.retries = retries
        self.timeout = timeout

    def get(self, path: str, **params) -> dict:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
        url = f"{self.base_url}{path}" + (f"?{query}" if query else "")
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        delay = 2.0
        for attempt in range(self.retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.load(resp)
            except urllib.error.HTTPError as e:
                if e.code not in (429, 500, 502, 503, 504) or attempt == self.retries - 1:
                    raise
            except (urllib.error.URLError, TimeoutError):
                if attempt == self.retries - 1:
                    raise
            time.sleep(delay)
            delay = min(delay * 1.7, 30)
        raise RuntimeError("unreachable")

    def paginate(self, path: str, key: str, max_pages: int = 200, **params):
        cursor = None
        for _ in range(max_pages):
            data = self.get(path, cursor=cursor, **params)
            yield from data.get(key) or []
            cursor = data.get("cursor")
            if not cursor:
                return
            time.sleep(self.pause)

    def open_markets(self, max_close_ts: int | None = None) -> list[dict]:
        """All open, plain binary markets (combo/parlay markets excluded)."""
        return list(self.paginate("/markets", "markets", limit=1000, status="open",
                                  mve_filter="exclude", max_close_ts=max_close_ts))

    def series(self) -> dict[str, dict]:
        """Series ticker -> series info (category, tags, fee multiplier)."""
        return {s["ticker"]: s for s in self.get("/series").get("series") or []}

    def event(self, event_ticker: str) -> dict:
        return self.get(f"/events/{urllib.parse.quote(event_ticker)}").get("event") or {}

    def markets_by_ticker(self, tickers: list[str]) -> list[dict]:
        out: list[dict] = []
        for i in range(0, len(tickers), 100):
            chunk = tickers[i:i + 100]
            out += self.get("/markets", tickers=",".join(chunk), limit=1000).get("markets") or []
            time.sleep(self.pause)
        return out


def series_ticker(event_ticker: str) -> str:
    return event_ticker.split("-", 1)[0]


def market_url(event_ticker: str) -> str:
    return f"https://kalshi.com/markets/{series_ticker(event_ticker).lower()}"
