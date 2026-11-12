"""Bet math: the single source of truth for every dollar figure the scanner shows.

All prices are in dollars per contract (0.01–0.99). A contract pays $1.00 if it
wins and $0.00 if it loses. See .claude/skills/bet-math/SKILL.md for the rules.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

CENT = 0.01


def ceil_cents(x: float) -> float:
    """Round a dollar amount up to the next cent (exchanges round fees up)."""
    return math.ceil(round(x * 100, 6)) / 100


@dataclass(frozen=True)
class FeeModel:
    """How much it costs to buy contracts, on top of the price.

    model:
      "robinhood" - flat commission + flat exchange fee per contract
                    (Robinhood's published pricing for event contracts).
      "kalshi"    - Kalshi's quadratic taker fee, ceil(rate * C * P * (1 - P)),
                    for people trading on Kalshi directly.
    """

    model: str = "robinhood"
    commission_per_contract: float = 0.01
    exchange_fee_per_contract: float = 0.01
    kalshi_taker_rate: float = 0.07

    def fees(self, contracts: int, price: float, multiplier: float = 1.0) -> float:
        if contracts <= 0:
            return 0.0
        if self.model == "kalshi":
            return ceil_cents(self.kalshi_taker_rate * multiplier * contracts * price * (1 - price))
        per = self.commission_per_contract + self.exchange_fee_per_contract
        return round(contracts * per, 2)


@dataclass(frozen=True)
class BetResult:
    stake: float            # the budget, e.g. 100
    price: float            # cost per contract (sum of legs for a bundle)
    contracts: int          # whole contracts bought
    cost: float             # contracts * price
    fees: float
    total_cost: float       # cost + fees: what actually leaves your account
    payout: float           # what you receive if it wins
    profit: float           # payout - total_cost
    return_pct: float       # profit / total_cost * 100
    annualized_pct: float | None
    max_loss: float         # what you lose if it loses (total_cost)
    breakeven_prob: float   # win chance needed to break even after fees
    days: float | None

    def to_dict(self) -> dict:
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in asdict(self).items()}


def max_contracts(stake: float, price: float, fee_model: FeeModel,
                  multiplier: float = 1.0, leg_prices: list[float] | None = None) -> int:
    """Largest whole number of contracts (per leg) whose price + fees fit in the stake."""
    if price <= 0:
        return 0
    c = int(stake // price)
    while c > 0:
        fees = _bundle_fees(c, price, fee_model, multiplier, leg_prices)
        if c * price + fees <= stake + 1e-9:
            return c
        c -= 1
    return 0


def _bundle_fees(c: int, price: float, fee_model: FeeModel, multiplier: float,
                 leg_prices: list[float] | None) -> float:
    """Fees for c contracts of a single market, or c contracts of every leg of a bundle."""
    if leg_prices:
        return round(sum(fee_model.fees(c, p, multiplier) for p in leg_prices), 2)
    return fee_model.fees(c, price, multiplier)


def annualize(return_frac: float, days: float | None, min_days: float = 1.0) -> float | None:
    """Compound a return over a year. Days are floored at `min_days` so a bet
    settling in two hours doesn't show a meaningless 10^40 % figure."""
    if days is None or return_frac <= -1:
        return None
    d = max(days, min_days)
    try:
        val = (1 + return_frac) ** (365 / d) - 1
    except OverflowError:
        return None
    return val * 100 if val < 1e6 else None


def bet(price: float, stake: float = 100.0, fee_model: FeeModel | None = None, days: float | None = None,
        multiplier: float = 1.0, leg_prices: list[float] | None = None) -> BetResult:
    """Outcome of spending up to `stake` dollars on a contract (or bundle) at `price`.

    For a bundle (arbitrage: buy every outcome), pass leg_prices; `price` is ignored
    and the bundle price is their sum. One contract of the bundle always pays $1.
    """
    fm = fee_model or FeeModel()
    if leg_prices:
        price = round(sum(leg_prices), 4)
    c = max_contracts(stake, price, fm, multiplier, leg_prices)
    cost = round(c * price, 2)
    fees = _bundle_fees(c, price, fm, multiplier, leg_prices) if c else 0.0
    total = round(cost + fees, 2)
    payout = float(c)
    profit = round(payout - total, 2)
    ret = profit / total if total else 0.0
    return BetResult(
        stake=stake, price=price, contracts=c, cost=cost, fees=fees, total_cost=total,
        payout=payout, profit=profit, return_pct=ret * 100,
        annualized_pct=annualize(ret, days), max_loss=total,
        breakeven_prob=(total / payout) if payout else 1.0, days=days,
    )


def expected_value(result: BetResult, win_prob: float) -> float:
    """Expected profit in dollars if the true chance of winning is `win_prob`."""
    return round(win_prob * result.payout - result.total_cost, 2)
