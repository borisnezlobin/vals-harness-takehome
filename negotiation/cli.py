import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from negotiation.agent import OpenRouterNegotiator
from negotiation.records import GameRecord, ModelStatsRecord, SummaryRecord
from negotiation.scenarios import SCENARIOS, Scenario, scenarios_by_name
from negotiation.settings import DEFAULT_MODELS, OPENROUTER_BASE_URL, MatchSettings
from negotiation.tournament import (
    CONFIG_FILE,
    SUMMARY_FILE,
    RunStore,
    Tournament,
    build_matchups,
    run_config,
)

DEFAULT_RUNS_DIR = Path("runs")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="negotiate", description="Buyer vs. seller negotiation eval"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="Play a round-robin tournament, or resume one")
    run.add_argument("--models", nargs="+", default=list(DEFAULT_MODELS))
    run.add_argument(
        "--scenarios", nargs="+", choices=[scenario.name for scenario in SCENARIOS], default=None
    )
    run.add_argument("--repeats", type=int, default=1)
    run.add_argument("--concurrency", type=int, default=6)
    run.add_argument("--turns", type=int, default=MatchSettings.turns_per_side)
    run.add_argument("--temperature", type=float, default=None)
    run.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    run.add_argument("--resume", type=Path, help="Run directory to finish")

    report = commands.add_parser("report", help="Print a run's leaderboard")
    report.add_argument("run_dir", type=Path, nargs="?", help="Defaults to the latest run")
    report.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    return parser


def latest_run(runs_dir: Path) -> Path:
    runs = sorted(path for path in runs_dir.glob("*") if (path / CONFIG_FILE).exists())
    if not runs:
        raise SystemExit(f"No runs in {runs_dir}/")
    return runs[-1]


def _new_store(
    args: argparse.Namespace,
) -> tuple[RunStore, list[str], list[Scenario], int, MatchSettings]:
    if len(set(args.models)) < 2:
        raise SystemExit("A round robin needs at least two different models.")
    settings = MatchSettings(turns_per_side=args.turns, temperature=args.temperature)
    scenarios = scenarios_by_name(args.scenarios)
    store = RunStore.create(args.runs_dir)
    store.write_config(run_config(store.run_id, args.models, scenarios, args.repeats, settings))
    return store, args.models, scenarios, args.repeats, settings


def _resumed_store(
    directory: Path,
) -> tuple[RunStore, list[str], list[Scenario], int, MatchSettings]:
    store = RunStore(directory)
    config = store.read_config()
    scenarios = [Scenario.from_record(record) for record in config["scenarios"]]
    settings = MatchSettings.from_record(config["settings"])
    return store, config["models"], scenarios, config["repeats"], settings


def _print_progress(done: int, total: int, game: GameRecord) -> None:
    outcome = game["outcome"]
    price = outcome["deal_price"]
    deal = "no deal" if price is None else f"deal at ${price:,}"
    print(
        f"[{done}/{total}] {game['game_id']}: {deal} after {outcome['turns_played']} turns",
        flush=True,
    )


async def _run(args: argparse.Namespace) -> None:
    load_dotenv()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENROUTER_API_KEY in .env or the environment.")
    store, models, scenarios, repeats, settings = (
        _resumed_store(args.resume) if args.resume else _new_store(args)
    )
    negotiator = OpenRouterNegotiator(api_key, OPENROUTER_BASE_URL, settings)
    matchups = build_matchups(models, scenarios, repeats)
    tournament = Tournament(
        negotiator, store, matchups, settings, args.concurrency, on_progress=_print_progress
    )
    print(f"Run {store.run_id}: {len(tournament.pending)} of {len(matchups)} games to play")
    await tournament.run()
    print(format_report(json.loads((store.directory / SUMMARY_FILE).read_text())))


def _score(value: float | None) -> str:
    return "-" if value is None else f"{value:+.3f}"


def _leaderboard_row(stats: ModelStatsRecord) -> str:
    deal_rate = f"{stats['deals']}/{stats['games']}"
    return (
        f"{stats['model']:<40} {_score(stats['mean_score']):>8} {_score(stats['buyer']['mean_score']):>8}"
        f" {_score(stats['seller']['mean_score']):>8} {deal_rate:>7} {stats['rejected_actions']:>8}"
        f" ${stats['cost_usd']:>7.4f}"
    )


def format_report(summary: SummaryRecord) -> str:
    header = f"{'model':<40} {'overall':>8} {'buyer':>8} {'seller':>8} {'deals':>7} {'rejects':>8} {'cost':>8}"
    status = (
        f"Run {summary['run_id']} ({summary['status']}): "
        f"{summary['completed_games']}/{summary['total_games']} games, ${summary['cost_usd']:.4f}"
    )
    rows = [_leaderboard_row(stats) for stats in summary["leaderboard"]]
    return "\n".join([status, "", header, *rows])


def _report(args: argparse.Namespace) -> None:
    directory = args.run_dir or latest_run(args.runs_dir)
    print(format_report(json.loads((directory / SUMMARY_FILE).read_text())))


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    if args.command == "run":
        try:
            asyncio.run(_run(args))
        except KeyboardInterrupt:
            sys.exit("Interrupted. Resume with: negotiate run --resume <run dir>")
    else:
        _report(args)
