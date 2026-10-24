from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from statistics import fmean

from negotiation.records import (
    SCHEMA_VERSION,
    GameRecord,
    ModelStatsRecord,
    PairingRecord,
    RoleName,
    RoleStatsRecord,
    RunStatus,
    ScenarioRecord,
    SummaryRecord,
)

ROLE_NAMES: tuple[RoleName, RoleName] = ("buyer", "seller")


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def mean_or_none(values: Iterable[float]) -> float | None:
    collected = list(values)
    return fmean(collected) if collected else None


def seller_share_of_split(price: int, scenario: ScenarioRecord) -> float:
    """Where the price sits between the two limits: 0 at the lower limit, 1 at the higher one.

    With overlapping limits this is the share of the surplus the seller kept. Without overlap it is
    the share of the shortfall the buyer absorbed, which is the same thing seen from the seller.
    """
    low = min(scenario["seller_minimum"], scenario["buyer_maximum"])
    high = max(scenario["seller_minimum"], scenario["buyer_maximum"])
    if high == low:
        return 0.5
    return (price - low) / (high - low)


def share_of_split(role: RoleName, game: GameRecord) -> float | None:
    price = game["outcome"]["deal_price"]
    if price is None:
        return None
    seller_share = seller_share_of_split(price, game["scenario"])
    return seller_share if role == "seller" else 1 - seller_share


def _role_stats(role: RoleName, games: list[GameRecord]) -> RoleStatsRecord:
    shares = (share_of_split(role, game) for game in games)
    return {
        "games": len(games),
        "deals": sum(1 for game in games if game["outcome"]["deal_price"] is not None),
        "mean_score": mean_or_none(game["scores"][role] for game in games),
        "mean_surplus_share": mean_or_none(share for share in shares if share is not None),
    }


def _games_by_role(games: list[GameRecord], model: str) -> dict[RoleName, list[GameRecord]]:
    return {role: [game for game in games if game["models"][role] == model] for role in ROLE_NAMES}


def _model_turn_totals(games: list[GameRecord], model: str) -> tuple[int, int, float]:
    rejected = errors = 0
    cost = 0.0
    for game in games:
        for turn in game["turns"]:
            if turn["model"] != model:
                continue
            rejected += len(turn["parse_problems"])
            rejected += sum(1 for action in turn["actions"] if not action["accepted"])
            errors += 1 if turn["error"] else 0
            cost += turn["usage"]["cost_usd"]
    return rejected, errors, cost


def model_stats(model: str, games: list[GameRecord]) -> ModelStatsRecord:
    by_role = _games_by_role(games, model)
    played = by_role["buyer"] + by_role["seller"]
    rejected, errors, cost = _model_turn_totals(played, model)
    scores = [game["scores"][role] for role in ROLE_NAMES for game in by_role[role]]
    return {
        "model": model,
        "games": len(played),
        "deals": sum(1 for game in played if game["outcome"]["deal_price"] is not None),
        "mean_score": mean_or_none(scores),
        "buyer": _role_stats("buyer", by_role["buyer"]),
        "seller": _role_stats("seller", by_role["seller"]),
        "mean_turns": mean_or_none(game["outcome"]["turns_played"] for game in played),
        "rejected_actions": rejected,
        "api_errors": errors,
        "cost_usd": cost,
    }


def _sort_key(stats: ModelStatsRecord) -> float:
    return stats["mean_score"] if stats["mean_score"] is not None else float("-inf")


def leaderboard(models: list[str], games: list[GameRecord]) -> list[ModelStatsRecord]:
    return sorted((model_stats(model, games) for model in models), key=_sort_key, reverse=True)


def pairings(games: list[GameRecord]) -> list[PairingRecord]:
    grouped: dict[tuple[str, str], list[GameRecord]] = defaultdict(list)
    for game in games:
        grouped[(game["models"]["buyer"], game["models"]["seller"])].append(game)
    return [
        {
            "buyer_model": buyer,
            "seller_model": seller,
            "games": len(group),
            "deals": sum(1 for game in group if game["outcome"]["deal_price"] is not None),
            "mean_buyer_score": mean_or_none(game["scores"]["buyer"] for game in group),
            "mean_seller_score": mean_or_none(game["scores"]["seller"] for game in group),
        }
        for (buyer, seller), group in sorted(grouped.items())
    ]


def summarize(
    run_id: str, models: list[str], games: list[GameRecord], total_games: int, status: RunStatus
) -> SummaryRecord:
    now = utc_now()
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "status": status,
        "updated_at": now,
        "finished_at": now if status == "finished" else None,
        "completed_games": len(games),
        "total_games": total_games,
        "cost_usd": sum(game["usage"]["cost_usd"] for game in games),
        "leaderboard": leaderboard(models, games),
        "pairings": pairings(games),
    }
