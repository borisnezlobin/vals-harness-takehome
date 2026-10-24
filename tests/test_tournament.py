import json
from pathlib import Path

import pytest
from openai.types.chat import ChatCompletionMessageParam

from negotiation.agent import ModelReply
from negotiation.records import GameRecord
from negotiation.scenarios import Scenario
from negotiation.settings import MatchSettings
from negotiation.tournament import (
    CONFIG_FILE,
    GAMES_FILE,
    SUMMARY_FILE,
    RunStore,
    Tournament,
    build_matchups,
    run_config,
)
from tests.conftest import ScriptedNegotiator, reply

MODELS = ["vendor/a", "vendor/b", "vendor/c"]


def test_round_robin_plays_every_ordered_pair(car: Scenario, no_overlap_car: Scenario) -> None:
    matchups = build_matchups(MODELS, [car, no_overlap_car], repeats=2)
    assert len(matchups) == 3 * 2 * 2 * 2
    for model in MODELS:
        assert sum(1 for matchup in matchups if matchup.buyer_model == model) == 8
        assert sum(1 for matchup in matchups if matchup.seller_model == model) == 8
    assert len({matchup.game_id for matchup in matchups}) == len(matchups)
    assert all("/" not in matchup.game_id for matchup in matchups)


def _store(tmp_path: Path, scenarios: list[Scenario], settings: MatchSettings) -> RunStore:
    store = RunStore.create(tmp_path)
    store.write_config(run_config(store.run_id, MODELS, scenarios, 1, settings))
    return store


async def test_tournament_writes_games_and_summary(tmp_path: Path, car: Scenario) -> None:
    settings = MatchSettings(turns_per_side=1)
    store = _store(tmp_path, [car], settings)
    progress: list[int] = []
    tournament = Tournament(
        ScriptedNegotiator(lambda model, messages: reply()),
        store,
        build_matchups(MODELS, [car], 1),
        settings,
        concurrency=2,
        on_progress=lambda done, total, game: progress.append(done),
    )
    await tournament.run()

    assert sorted(progress) == [1, 2, 3, 4, 5, 6]
    assert (store.directory / CONFIG_FILE).exists()
    lines = (store.directory / GAMES_FILE).read_text().splitlines()
    assert len(lines) == 6
    summary = json.loads((store.directory / SUMMARY_FILE).read_text())
    assert summary["status"] == "finished"
    assert summary["completed_games"] == 6
    assert summary["total_games"] == 6
    assert summary["finished_at"] is not None
    assert len(summary["leaderboard"]) == 3


async def test_resume_skips_finished_games(tmp_path: Path, car: Scenario) -> None:
    settings = MatchSettings(turns_per_side=1)
    store = _store(tmp_path, [car], settings)
    matchups = build_matchups(MODELS, [car], 1)
    first = Tournament(
        ScriptedNegotiator(lambda model, messages: reply()), store, matchups[:2], settings, 1
    )
    await first.run()

    negotiator = ScriptedNegotiator(lambda model, messages: reply())
    resumed = Tournament(negotiator, RunStore(store.directory), matchups, settings, 1)
    assert len(resumed.pending) == 4
    games: list[GameRecord] = await resumed.run()
    assert len(games) == 6
    assert len(negotiator.calls) == 4 * 2


async def test_interrupted_run_is_marked(tmp_path: Path, car: Scenario) -> None:
    settings = MatchSettings(turns_per_side=1)
    store = _store(tmp_path, [car], settings)

    def explode(model: str, messages: list[ChatCompletionMessageParam]) -> ModelReply:
        raise RuntimeError("network gone")

    tournament = Tournament(
        ScriptedNegotiator(explode),
        store,
        build_matchups(MODELS, [car], 1),
        settings,
        1,
    )
    with pytest.raises(RuntimeError, match="network gone"):
        await tournament.run()
    summary = json.loads((store.directory / SUMMARY_FILE).read_text())
    assert summary["status"] == "interrupted"


def test_config_round_trips_settings_and_scenarios(tmp_path: Path, car: Scenario) -> None:
    settings = MatchSettings(turns_per_side=3, temperature=0.4)
    store = _store(tmp_path, [car], settings)
    config = store.read_config()
    assert MatchSettings.from_record(config["settings"]) == settings
    assert [Scenario.from_record(record) for record in config["scenarios"]] == [car]
    assert config["total_games"] == 6
