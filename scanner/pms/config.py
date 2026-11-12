from __future__ import annotations

import tomllib
from pathlib import Path

DEFAULTS = {
    "bet": {"stake": 100.0},
    "fees": {"model": "robinhood", "commission_per_contract": 0.01,
             "exchange_fee_per_contract": 0.01, "kalshi_taker_rate": 0.07},
    "favorites": {"enabled": True, "min_price": 0.85, "max_price": 0.97, "max_days_to_settle": 7,
                  "min_volume_24h": 500, "max_spread": 0.03, "max_per_event": 3, "min_profit": 1.0},
    "arbitrage": {"enabled": True, "max_days_to_settle": 60, "min_profit": 0.5, "min_volume_24h": 10},
    "output": {"max_opportunities": 200},
    "categories": {"include": [], "exclude": []},
}


def load_config(path: Path | None = None) -> dict:
    cfg = {k: dict(v) for k, v in DEFAULTS.items()}
    if path and Path(path).exists():
        with open(path, "rb") as fh:
            user = tomllib.load(fh)
        for section, values in user.items():
            cfg.setdefault(section, {}).update(values)
    return cfg
