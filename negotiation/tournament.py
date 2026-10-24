import asyncio
import itertools
import json
import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from negotiation.agent import Negotiator
from negotiation.analysis import summarize, utc_now
from negotiation.match import Matchup, run_negotiation
from negotiation.records import SCHEMA_VERSION, GameRecord, RunConfigRecord, RunStatus
from negotiation.scenarios import Scenario
from negotiation.settings import MatchSettings

CONFIG_FILE = "config.json"
GAMES_FILE = "games.jsonl"
SUMMARY_FILE = "summary.json"


def game_id_for(scenario: Scenario, buyer: str, seller: str, repeat: int) -> str:
    slug = f"{scenario.name}--{buyer}--vs--{seller}--r{repeat}"
    return slug.replace("/", "_").replace(":", "_")


def build_matchups(models: list[str], scenarios: list[Scenario], repeats: int) -> list[Matchup]:
    pairs = list(itertools.permutations(models, 2))
    return [
        Matchup(game_id_for(scenario, buyer, seller, repeat), scenario, buyer, seller, repeat)
        for repeat, scenario, (buyer, seller) in itertools.product(range(repeats), scenarios, pairs)
    ]


def write_json_atomically(path: Path, payload: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2))
    os.replace(temporary, path)


class RunStore:
    def __init__(self, directory: Path):
        self.directory = directory

    @classmethod
    def create(cls, root: Path) -> "RunStore":
        directory = root / datetime.now().strftime("%Y%m%d-%H%M%S")
        directory.mkdir(parents=True, exist_ok=False)
        return cls(directory)

    @property
    def run_id(self) -> str:
        return self.directory.name

    def write_config(self, config: RunConfigRecord) -> None:
        write_json_atomically(self.directory / CONFIG_FILE, config)

    def read_config(self) -> RunConfigRecord:
        return json.loads((self.directory / CONFIG_FILE).read_text())

    def append_game(self, game: GameRecord) -> None:
        with (self.directory / GAMES_FILE).open("a") as handle:
            handle.write(json.dumps(game) + "\n")

    def load_games(self) -> list[GameRecord]:
        path = self.directory / GAMES_FILE
        if not path.exists():
            return []
        with path.open() as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def write_summary(self, games: list[GameRecord], status: RunStatus) -> None:
        config = self.read_config()
        summary = summarize(self.run_id, config["models"], games, config["total_games"], status)
        write_json_atomically(self.directory / SUMMARY_FILE, summary)


def run_config(
    run_id: str,
    models: list[str],
    scenarios: list[Scenario],
    repeats: int,
    settings: MatchSettings,
) -> RunConfigRecord:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "started_at": utc_now(),
        "models": models,
        "scenarios": [scenario.to_record() for scenario in scenarios],
        "repeats": repeats,
        "total_games": len(build_matchups(models, scenarios, repeats)),
        "settings": settings.to_record(),
    }


ProgressCallback = Callable[[int, int, GameRecord], None]


class Tournament:
    def __init__(
        self,
        negotiator: Negotiator,
        store: RunStore,
        matchups: list[Matchup],
        settings: MatchSettings,
        concurrency: int,
        on_progress: ProgressCallback | None = None,
    ):
        self.negotiator = negotiator
        self.store = store
        self.settings = settings
        self.games = store.load_games()
        finished_ids = {game["game_id"] for game in self.games}
        self.pending = [matchup for matchup in matchups if matchup.game_id not in finished_ids]
        self.total = len(matchups)
        self.limiter = asyncio.Semaphore(concurrency)
        self.on_progress = on_progress

    async def run(self) -> list[GameRecord]:
        self.store.write_summary(self.games, "running")
        try:
            await asyncio.gather(*(self._play(matchup) for matchup in self.pending))
        except BaseException:
            self.store.write_summary(self.games, "interrupted")
            raise
        self.store.write_summary(self.games, "finished")
        return self.games

    async def _play(self, matchup: Matchup) -> None:
        async with self.limiter:
            game = await run_negotiation(self.negotiator, matchup, self.settings)
        self.games.append(game)
        self.store.append_game(game)
        self.store.write_summary(self.games, "running")
        if self.on_progress:
            self.on_progress(len(self.games), self.total, game)
