import math

import pytest

from negotiation.roles import Role
from negotiation.scenarios import Scenario
from negotiation.scoring import bounded_score, normalized_surplus, score_outcome


def test_surplus_is_measured_against_the_midpoint_of_the_limits(car: Scenario) -> None:
    assert normalized_surplus(Role.SELLER, 555, car) == pytest.approx(55 / 550)
    assert normalized_surplus(Role.BUYER, 555, car) == pytest.approx(45 / 550)


def test_surplus_scales_with_price() -> None:
    small = Scenario("small", "x", seller_minimum=500, buyer_maximum=500)
    large = Scenario("large", "x", seller_minimum=50_000, buyer_maximum=50_000)
    assert normalized_surplus(Role.SELLER, 750, small) == normalized_surplus(
        Role.SELLER, 75_000, large
    )


def test_gains_are_linear() -> None:
    assert bounded_score(0.3) == pytest.approx(0.3)


def test_losses_are_smooth_at_zero() -> None:
    epsilon = 1e-6
    slope = (bounded_score(0) - bounded_score(-epsilon)) / epsilon
    assert slope == pytest.approx(1, rel=1e-3)


def test_huge_losses_flatten_toward_the_penalty() -> None:
    assert bounded_score(-19) == pytest.approx(-1, abs=1e-6)
    assert bounded_score(-18) == pytest.approx(bounded_score(-19), abs=1e-6)
    assert bounded_score(-19) > -1


def test_penalty_size_is_configurable() -> None:
    assert bounded_score(-1000, max_penalty=2.0) == pytest.approx(-2.0)
    assert bounded_score(-0.5, max_penalty=2.0) == pytest.approx(-2 * (1 - math.exp(-0.25)))


def test_no_deal_gets_exactly_the_penalty(car: Scenario) -> None:
    assert score_outcome(Role.BUYER, None, car) == -1
    assert score_outcome(Role.SELLER, None, car, max_penalty=3) == -3


@pytest.mark.parametrize("price", [1, 450, 10_000, 1_000_000])
def test_any_deal_beats_no_deal(car: Scenario, price: int) -> None:
    for role in Role:
        assert score_outcome(role, price, car) > score_outcome(role, None, car)


def test_no_overlap_midpoint_splits_the_loss_evenly(no_overlap_car: Scenario) -> None:
    buyer = score_outcome(Role.BUYER, 550, no_overlap_car)
    seller = score_outcome(Role.SELLER, 550, no_overlap_car)
    assert buyer == pytest.approx(seller)
    assert buyer < 0


def test_no_overlap_prices_favor_the_side_they_lean_toward(no_overlap_car: Scenario) -> None:
    assert score_outcome(Role.BUYER, 525, no_overlap_car) > score_outcome(
        Role.SELLER, 525, no_overlap_car
    )
    assert score_outcome(Role.SELLER, 675, no_overlap_car) > score_outcome(
        Role.BUYER, 675, no_overlap_car
    )
