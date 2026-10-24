import math

from negotiation.roles import Role
from negotiation.scenarios import Scenario

MAX_PENALTY = 1.0

# 1 - exp(x) rounds to exactly 1.0 once x < -37, which would tie an absurd deal with no deal.
DEAL_FLOOR_GAP = 1e-9


def normalized_surplus(role: Role, price: int, scenario: Scenario) -> float:
    if role is Role.SELLER:
        surplus = price - scenario.seller_minimum
    else:
        surplus = scenario.buyer_maximum - price
    return surplus / scenario.reference_price


def bounded_score(surplus: float, max_penalty: float = MAX_PENALTY) -> float:
    """Linear for gains; losses decay smoothly toward -max_penalty without reaching it."""
    if surplus >= 0:
        return surplus
    loss = -max_penalty * (1 - math.exp(surplus / max_penalty))
    return max(loss, -max_penalty * (1 - DEAL_FLOOR_GAP))


def score_outcome(
    role: Role, deal_price: int | None, scenario: Scenario, max_penalty: float = MAX_PENALTY
) -> float:
    if deal_price is None:
        return -max_penalty
    return bounded_score(normalized_surplus(role, deal_price, scenario), max_penalty)
