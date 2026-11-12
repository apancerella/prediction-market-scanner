"""Run a scan: fetch open markets, find opportunities, write latest.json, update the pick ledger.

    cd scanner && python -m pms.scan                 # writes to ../web/public/data
    cd scanner && python -m pms.scan --out ../data   # custom folder
    cd scanner && python -m pms.scan --dry-run       # print a summary, write nothing
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

from .betmath import FeeModel
from .config import load_config
from .kalshi import KalshiClient
from .strategies import arbitrage, favorites, score
from .track import update_ledger

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "web" / "public" / "data"


def fee_model_from(cfg: dict) -> FeeModel:
    f = cfg["fees"]
    return FeeModel(model=f["model"], commission_per_contract=f["commission_per_contract"],
                    exchange_fee_per_contract=f["exchange_fee_per_contract"],
                    kalshi_taker_rate=f["kalshi_taker_rate"])


def category_ok(o: dict, cfg: dict) -> bool:
    inc, exc = cfg["categories"]["include"], cfg["categories"]["exclude"]
    return (not inc or o["category"] in inc) and o["category"] not in exc


def run_scan(cfg: dict, client: KalshiClient, now: dt.datetime | None = None,
             markets: list[dict] | None = None, series: dict | None = None) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    horizon = max(cfg["favorites"]["max_days_to_settle"], cfg["arbitrage"]["max_days_to_settle"])
    t0 = time.time()
    if markets is None:
        # Close time can be later than settlement (e.g. games close 2 weeks out), so look wider.
        markets = client.open_markets(max_close_ts=int(now.timestamp() + (horizon + 21) * 86400))
    if series is None:
        series = client.series()
    fm = fee_model_from(cfg)
    stake = cfg["bet"]["stake"]
    opps: list[dict] = []
    if cfg["favorites"]["enabled"]:
        opps += favorites(markets, series, cfg, fm, stake, now)
    if cfg["arbitrage"]["enabled"]:
        opps += arbitrage(markets, series, cfg, fm, stake, now, fetch_event=client.event)
    opps = [o for o in opps if category_ok(o, cfg)]
    for o in opps:
        o["score"] = round(score(o), 4)
    opps.sort(key=lambda o: o["score"], reverse=True)
    opps = opps[: cfg["output"]["max_opportunities"]]
    return {
        "generated_at": now.isoformat(),
        "source": "Kalshi public market data (the exchange behind Robinhood prediction markets)",
        "markets_scanned": len(markets),
        "scan_seconds": round(time.time() - t0, 1),
        "stake": stake,
        "fee_model": cfg["fees"],
        "criteria": {"favorites": cfg["favorites"], "arbitrage": cfg["arbitrage"]},
        "opportunities": opps,
    }


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    tmp.replace(path)


def summarize(result: dict, limit: int = 15) -> str:
    opps = result["opportunities"]
    lines = [f"Scanned {result['markets_scanned']:,} markets in {result['scan_seconds']}s; "
             f"{len(opps)} opportunities (stake ${result['stake']:.0f})", ""]
    for o in opps[:limit]:
        b = o["bet"]
        lines.append(f"{o['strategy']:<9} {o['price']*100:5.1f}¢  +${b['profit']:6.2f} "
                     f"({b['return_pct']:5.2f}%)  risk ${b['max_loss']:.2f}  "
                     f"{o['days_to_settle'] or 0:5.2f}d  [{o['category']}] {o['title'][:60]} -> {o['outcome'][:40]}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="folder for latest.json and picks.json")
    ap.add_argument("--config", type=Path, default=ROOT / "config.toml")
    ap.add_argument("--dry-run", action="store_true", help="print a summary only")
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    client = KalshiClient()
    result = run_scan(cfg, client)
    print(summarize(result, args.top))
    if args.dry_run:
        return 0
    write_json(args.out / "latest.json", result)
    ledger_path = args.out / "picks.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else None
    ledger = update_ledger(ledger, result, client)
    write_json(ledger_path, ledger)
    print(f"\nWrote {args.out / 'latest.json'} and {ledger_path} "
          f"({ledger['summary']['resolved']} resolved picks tracked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
