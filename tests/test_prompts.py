from negotiation.game import NegotiationState
from negotiation.prompts import status_block, system_prompt
from negotiation.roles import Role
from negotiation.scenarios import Scenario
from negotiation.settings import MatchSettings


def test_each_side_sees_only_its_own_limit(car: Scenario) -> None:
    settings = MatchSettings()
    buyer = system_prompt(Role.BUYER, car, settings)
    seller = system_prompt(Role.SELLER, car, settings)
    assert "$600" in buyer
    assert "$500" not in buyer
    assert "$500" in seller
    assert "$600" not in seller


def test_prompt_states_the_rules(car: Scenario) -> None:
    prompt = system_prompt(Role.BUYER, car, MatchSettings(turns_per_side=7, message_char_limit=250))
    assert "7 turns" in prompt
    assert "250 characters" in prompt
    assert "Any deal, even a bad one, scores better than no deal" in prompt


def test_status_block_reports_state_and_problems() -> None:
    state = NegotiationState()
    state.apply_turn(Role.SELLER, [])
    block = status_block(
        Role.BUYER,
        state,
        {Role.BUYER: 3, Role.SELLER: 2},
        "propose_offer($400)",
        ["accept_offer(1) was rejected: nope"],
    )
    assert "Turns you have left, including this one: 3" in block
    assert "Tools you called last turn: propose_offer($400)" in block
    assert "Problems with your last turn: accept_offer(1) was rejected: nope" in block
