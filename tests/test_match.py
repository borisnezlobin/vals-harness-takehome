from openai.types.chat import ChatCompletionMessageParam

from negotiation.agent import ModelReply
from negotiation.match import Matchup, run_negotiation
from negotiation.scenarios import Scenario
from negotiation.settings import MatchSettings
from tests.conftest import ScriptedNegotiator, accept, end, propose, reply

BUYER = "test/buyer"
SELLER = "test/seller"


def _matchup(scenario: Scenario) -> Matchup:
    return Matchup("game", scenario, BUYER, SELLER, repeat=0)


def _turn_number(messages: list[ChatCompletionMessageParam]) -> int:
    return sum(1 for message in messages if message["role"] == "user")


async def test_quick_deal_ends_once_both_sides_ask(car: Scenario) -> None:
    def script(model: str, messages: list[ChatCompletionMessageParam]) -> ModelReply:
        turn = _turn_number(messages)
        if model == BUYER:
            return reply(propose(540), text="540?") if turn == 1 else reply(end())
        return reply(accept(540), end())

    game = await run_negotiation(ScriptedNegotiator(script), _matchup(car), MatchSettings())
    assert game["outcome"]["deal_price"] == 540
    assert game["outcome"]["deal_accepted_by"] == "seller"
    assert game["outcome"]["ended_by_agreement"]
    assert game["outcome"]["turns_played"] == 3
    assert game["scores"]["seller"] > 0
    assert game["scores"]["buyer"] > 0
    assert [turn["role"] for turn in game["turns"]] == ["buyer", "seller", "buyer"]
    assert game["turns"][0]["standing_offers"] == {"buyer": 540, "seller": None}


async def test_runs_the_full_turn_budget_without_agreement(car: Scenario) -> None:
    negotiator = ScriptedNegotiator(lambda model, messages: reply())
    settings = MatchSettings(turns_per_side=4)
    game = await run_negotiation(negotiator, _matchup(car), settings)
    assert game["outcome"]["turns_played"] == 8
    assert game["outcome"]["deal_price"] is None
    assert game["scores"] == {"buyer": -1.0, "seller": -1.0}


async def test_long_messages_are_truncated(car: Scenario) -> None:
    negotiator = ScriptedNegotiator(lambda model, messages: reply(text="x" * 50))
    game = await run_negotiation(
        negotiator, _matchup(car), MatchSettings(turns_per_side=1, message_char_limit=20)
    )
    turn = game["turns"][0]
    assert turn["text"] == "x" * 20
    assert turn["truncated"]
    assert turn["original_length"] == 50


async def test_opponent_sees_message_actions_and_rejections(car: Scenario) -> None:
    def script(model: str, messages: list[ChatCompletionMessageParam]) -> ModelReply:
        if model == BUYER:
            return reply(propose(450), text="Cash today.")
        return reply(accept(999))

    negotiator = ScriptedNegotiator(script)
    await run_negotiation(negotiator, _matchup(car), MatchSettings(turns_per_side=2))
    seller_first_prompt = str(negotiator.calls[1][1][-1].get("content"))
    assert "Cash today." in seller_first_prompt
    assert "propose_offer($450)" in seller_first_prompt
    seller_second_prompt = str(negotiator.calls[3][1][-1].get("content"))
    assert "accept_offer(999) was rejected" in seller_second_prompt


async def test_action_summaries_stay_out_of_the_models_own_messages(car: Scenario) -> None:
    negotiator = ScriptedNegotiator(lambda model, messages: reply(propose(500), text="Hi"))
    await run_negotiation(negotiator, _matchup(car), MatchSettings(turns_per_side=2))
    _, history = negotiator.calls[-1]
    own_messages = [message.get("content") for message in history if message["role"] == "assistant"]
    assert own_messages == ["Hi"]


async def test_usage_is_totalled(car: Scenario) -> None:
    def script(model: str, messages: list[ChatCompletionMessageParam]) -> ModelReply:
        result = reply()
        result.usage = {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "reasoning_tokens": 2,
            "cost_usd": 0.01,
        }
        return result

    game = await run_negotiation(
        ScriptedNegotiator(script), _matchup(car), MatchSettings(turns_per_side=2)
    )
    assert game["usage"]["prompt_tokens"] == 40
    assert abs(game["usage"]["cost_usd"] - 0.04) < 1e-9


async def test_api_errors_are_counted(car: Scenario) -> None:
    negotiator = ScriptedNegotiator(
        lambda model, messages: ModelReply(text="", actions=[], error="boom")
    )
    game = await run_negotiation(negotiator, _matchup(car), MatchSettings(turns_per_side=1))
    assert game["outcome"]["api_errors"] == 2
