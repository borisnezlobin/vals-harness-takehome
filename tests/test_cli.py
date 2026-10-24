import json
from pathlib import Path

import pytest

from negotiation.cli import format_report, latest_run, main
from negotiation.scenarios import Scenario
from negotiation.settings import MatchSettings
from negotiation.tournament import RunStore, Tournament, build_matchups, run_config
from tests.conftest import ScriptedNegotiator, reply


async def _finished_run(root: Path, scenario: Scenario) -> RunStore:
    models = ["vendor/a", "vendor/b"]
    settings = MatchSettings(turns_per_side=1)
    store = RunStore.create(root)
    store.write_config(run_config(store.run_id, models, [scenario], 1, settings))
    negotiator = ScriptedNegotiator(lambda model, messages: reply())
    await Tournament(negotiator, store, build_matchups(models, [scenario], 1), settings, 1).run()
    return store


async def test_format_report_lists_every_model(tmp_path: Path, car: Scenario) -> None:
    store = await _finished_run(tmp_path, car)
    report = format_report(json.loads((store.directory / "summary.json").read_text()))
    assert "(finished): 2/2 games" in report
    assert "vendor/a" in report
    assert "vendor/b" in report


async def test_report_command_reads_latest_run(
    tmp_path: Path, car: Scenario, capsys: pytest.CaptureFixture[str]
) -> None:
    store = await _finished_run(tmp_path, car)
    assert latest_run(tmp_path) == store.directory
    main(["report", "--runs-dir", str(tmp_path)])
    assert store.run_id in capsys.readouterr().out


def test_latest_run_without_runs(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        latest_run(tmp_path)


def test_run_needs_two_models(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    with pytest.raises(SystemExit, match="two different models"):
        main(["run", "--models", "a/x", "a/x", "--runs-dir", str(tmp_path)])
