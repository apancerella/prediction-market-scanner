import pytest

from pms.betmath import FeeModel, annualize, bet, ceil_cents, expected_value

RH = FeeModel()  # $0.01 commission + $0.01 exchange fee per contract


def test_robinhood_fees_at_92_cents():
    b = bet(0.92, 100, RH, days=2)
    # 0.94 all-in per contract -> 106 contracts
    assert b.contracts == 106
    assert b.cost == pytest.approx(97.52)
    assert b.fees == pytest.approx(2.12)
    assert b.total_cost == pytest.approx(99.64)
    assert b.payout == 106
    assert b.profit == pytest.approx(6.36)
    assert b.max_loss == b.total_cost
    assert b.total_cost <= 100


def test_never_spends_more_than_stake():
    for cents in range(1, 100):
        b = bet(cents / 100, 100, RH)
        assert b.total_cost <= 100 + 1e-9
        # one more contract would not fit
        assert (b.contracts + 1) * (cents / 100 + 0.02) > 100


def test_kalshi_quadratic_fee_rounds_up():
    km = FeeModel(model="kalshi")
    # 0.07 * 100 * 0.5 * 0.5 = 1.75
    assert km.fees(100, 0.5) == pytest.approx(1.75)
    # 0.07 * 1 * 0.95 * 0.05 = 0.003325 -> rounds up to 1 cent
    assert km.fees(1, 0.95) == pytest.approx(0.01)
    assert ceil_cents(1.231) == pytest.approx(1.24)


def test_high_price_profit_is_small_and_loss_is_whole_stake():
    b = bet(0.97, 100, RH)
    assert b.profit < 2
    assert b.max_loss > 99


def test_bundle_for_arbitrage():
    b = bet(0, 100, RH, leg_prices=[0.40, 0.45])  # costs 0.85 + 0.04 fees per set
    assert b.price == pytest.approx(0.85)
    assert b.contracts == 112
    assert b.payout == 112
    assert b.fees == pytest.approx(4.48)
    assert b.profit == pytest.approx(112 - 95.2 - 4.48)


def test_breakeven_and_ev():
    b = bet(0.90, 100, RH)
    assert b.breakeven_prob == pytest.approx(b.total_cost / b.payout)
    assert expected_value(b, b.breakeven_prob) == pytest.approx(0, abs=0.01)
    assert expected_value(b, 1.0) == pytest.approx(b.profit)


def test_annualize_floors_short_bets():
    assert annualize(0.01, 0.01) == pytest.approx(annualize(0.01, 1.0))
    assert annualize(0.05, None) is None
    assert annualize(5.0, 0.1) is None  # absurd numbers are suppressed
