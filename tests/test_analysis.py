import pytest
from openai.types.chat import ChatCompletionMessageParam

from negotiation.agent import ModelReply
from negotiation.analysis import leaderboard, pairings, seller_share_of_split
from negotiation.match import Matchup, run_negotiation
from negotiation.records import GameRecord
from negotiation.scenarios import Scenario
from negotiation.settings import MatchSettings
from tests.conftest import ScriptedNegotiator, accept, propose, reply


def test_share_of_split_with_overlap(car: Scenario) -> None:
    record = car.to_record()
    assert seller_share_of_split(500, record) == 0
    assert seller_share_of_split(600, record) == 1
    assert seller_share_of_split(575, record) == pytest.approx(0.75)


def test_share_of_split_without_overlap(no_overlap_car: Scenario) -> None:
    record = no_overlap_car.to_record()
    assert seller_share_of_split(525, record) == pytest.approx(0.25)
    assert seller_share_of_split(550, record) == pytest.approx(0.5)


def test_share_of_split_with_equal_limits() -> None:
    record = Scenario("tie", "x", 500, 500).to_record()
    assert seller_share_of_split(700, record) == 0.5


async def _game(scenario: Scenario, buyer: str, seller: str, price: int | None) -> GameRecord:
    def script(model: str, messages: list[ChatCompletionMessageParam]) -> ModelReply:
        if price is None:
            return reply()
        return reply(propose(price)) if model == buyer else reply(accept(price))

    negotiator = ScriptedNegotiator(script)
    matchup = Matchup(f"{buyer}-{seller}-{price}", scenario, buyer, seller, 0)
    return await run_negotiation(negotiator, matchup, MatchSettings(turns_per_side=1))


async def test_leaderboard_ranks_models_by_mean_score(car: Scenario) -> None:
    games = [
        await _game(car, "a", "b", 590),
        await _game(car, "b", "a", 510),
    ]
    board = leaderboard(["a", "b"], games)
    assert [stats["model"] for stats in board] == ["b", "a"]
    winner = board[0]
    assert winner["games"] == 2
    assert winner["deals"] == 2
    assert winner["seller"]["mean_surplus_share"] == pytest.approx(0.9)
    assert winner["buyer"]["mean_surplus_share"] == pytest.approx(0.9)


async def test_leaderboard_counts_no_deals(car: Scenario) -> None:
    games = [await _game(car, "a", "b", None)]
    stats = {entry["model"]: entry for entry in leaderboard(["a", "b"], games)}
    assert stats["a"]["deals"] == 0
    assert stats["a"]["buyer"]["mean_score"] == -1
    assert stats["a"]["buyer"]["mean_surplus_share"] is None
    assert stats["a"]["seller"]["games"] == 0
    assert stats["a"]["seller"]["mean_score"] is None


async def test_pairings_group_by_buyer_and_seller(car: Scenario) -> None:
    games = [
        await _game(car, "a", "b", 550),
        await _game(car, "a", "b", 560),
        await _game(car, "b", "a", 540),
    ]
    rows = {(row["buyer_model"], row["seller_model"]): row for row in pairings(games)}
    assert rows[("a", "b")]["games"] == 2
    assert rows[("b", "a")]["games"] == 1
