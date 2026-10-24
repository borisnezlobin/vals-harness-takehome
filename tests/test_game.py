from negotiation.game import Action, ActionKind, NegotiationState
from negotiation.roles import Role
from tests.conftest import accept, end, propose


def test_proposal_sets_standing_offer() -> None:
    state = NegotiationState()
    [result] = state.apply_turn(Role.BUYER, [propose(400)])
    assert result.accepted
    assert state.standing_offers[Role.BUYER] == 400


def test_accept_must_match_the_latest_offer() -> None:
    state = NegotiationState()
    state.apply_turn(Role.BUYER, [propose(400)])
    state.apply_turn(Role.BUYER, [propose(450)])
    [result] = state.apply_turn(Role.SELLER, [accept(400)])
    assert not result.accepted
    assert "$450" in result.note
    assert state.deal is None


def test_accept_without_any_offer_is_rejected() -> None:
    state = NegotiationState()
    [result] = state.apply_turn(Role.SELLER, [accept(400)])
    assert not result.accepted
    assert "not made an offer" in result.note


def test_cannot_accept_your_own_offer() -> None:
    state = NegotiationState()
    state.apply_turn(Role.BUYER, [propose(400)])
    [result] = state.apply_turn(Role.BUYER, [accept(400)])
    assert not result.accepted


def test_accepting_locks_a_deal_without_ending() -> None:
    state = NegotiationState()
    state.apply_turn(Role.BUYER, [propose(400)])
    state.apply_turn(Role.SELLER, [accept(400)])
    assert state.deal is not None
    assert state.deal.price == 400
    assert state.deal.accepted_by is Role.SELLER
    assert not state.ended_by_agreement


def test_later_acceptance_replaces_the_deal() -> None:
    state = NegotiationState()
    state.apply_turn(Role.BUYER, [propose(400)])
    state.apply_turn(Role.SELLER, [accept(400), propose(550)])
    state.apply_turn(Role.BUYER, [accept(550)])
    assert state.deal is not None
    assert state.deal.price == 550


def test_propose_and_accept_in_one_turn() -> None:
    state = NegotiationState()
    state.apply_turn(Role.BUYER, [propose(400)])
    results = state.apply_turn(Role.SELLER, [accept(400), propose(420)])
    assert all(result.accepted for result in results)
    assert state.standing_offers[Role.SELLER] == 420


def test_ending_needs_both_sides() -> None:
    state = NegotiationState()
    state.apply_turn(Role.BUYER, [end()])
    assert not state.ended_by_agreement
    state.apply_turn(Role.SELLER, [end()])
    assert state.ended_by_agreement


def test_a_new_offer_cancels_pending_end_requests() -> None:
    state = NegotiationState()
    state.apply_turn(Role.BUYER, [end()])
    state.apply_turn(Role.SELLER, [propose(550)])
    state.apply_turn(Role.BUYER, [])
    assert not state.end_requested[Role.BUYER]
    state.apply_turn(Role.SELLER, [end()])
    assert not state.ended_by_agreement


def test_repeating_the_same_offer_keeps_end_requests() -> None:
    state = NegotiationState()
    state.apply_turn(Role.SELLER, [propose(550)])
    state.apply_turn(Role.BUYER, [end()])
    state.apply_turn(Role.SELLER, [propose(550), end()])
    assert state.ended_by_agreement


def test_proposing_and_ending_in_one_turn_still_asks_to_end() -> None:
    state = NegotiationState()
    state.apply_turn(Role.BUYER, [propose(500), end()])
    assert state.end_requested[Role.BUYER]


def test_non_positive_prices_are_rejected() -> None:
    state = NegotiationState()
    results = state.apply_turn(Role.BUYER, [propose(0), propose(-5), Action(ActionKind.PROPOSE)])
    assert not any(result.accepted for result in results)
    assert state.standing_offers[Role.BUYER] is None


def test_action_record_uses_tool_names() -> None:
    state = NegotiationState()
    [result] = state.apply_turn(Role.BUYER, [propose(400)])
    assert result.to_record() == {
        "kind": "propose_offer",
        "price": 400,
        "accepted": True,
        "note": "standing offer is now $400",
    }
