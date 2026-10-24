"""Shapes of the JSON files a run writes. The dashboard reads these, so keep them in sync with
dashboard/lib/types.ts and bump SCHEMA_VERSION on breaking changes."""

from typing import Literal, TypedDict

SCHEMA_VERSION = 1

RoleName = Literal["buyer", "seller"]
ActionName = Literal["propose_offer", "accept_offer", "end_negotiation"]
RunStatus = Literal["running", "finished", "interrupted"]


class ActionRecord(TypedDict):
    kind: ActionName
    price: int | None
    accepted: bool
    note: str


class UsageRecord(TypedDict):
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int
    cost_usd: float


class TurnRecord(TypedDict):
    index: int
    role: RoleName
    model: str
    provider: str | None
    text: str
    truncated: bool
    original_length: int
    reasoning: str | None
    actions: list[ActionRecord]
    parse_problems: list[str]
    raw_tool_calls: list[dict[str, str]]
    standing_offers: dict[RoleName, int | None]
    deal_after_turn: int | None
    usage: UsageRecord
    latency_seconds: float
    error: str | None


class ScenarioRecord(TypedDict):
    name: str
    item: str
    seller_minimum: int
    buyer_maximum: int
    reference_price: float
    reserves_overlap: bool


class OutcomeRecord(TypedDict):
    deal_price: int | None
    deal_accepted_by: RoleName | None
    ended_by_agreement: bool
    turns_played: int
    api_errors: int
    rejected_actions: int


class GameRecord(TypedDict):
    schema_version: int
    game_id: str
    repeat: int
    scenario: ScenarioRecord
    models: dict[RoleName, str]
    outcome: OutcomeRecord
    scores: dict[RoleName, float]
    usage: UsageRecord
    turns: list[TurnRecord]


class SettingsRecord(TypedDict):
    turns_per_side: int
    message_char_limit: int
    max_penalty: float
    max_output_tokens: int
    temperature: float | None
    request_attempts: int


class RunConfigRecord(TypedDict):
    schema_version: int
    run_id: str
    started_at: str
    models: list[str]
    scenarios: list[ScenarioRecord]
    repeats: int
    total_games: int
    settings: SettingsRecord


class RoleStatsRecord(TypedDict):
    games: int
    deals: int
    mean_score: float | None
    mean_surplus_share: float | None


class ModelStatsRecord(TypedDict):
    model: str
    games: int
    deals: int
    mean_score: float | None
    buyer: RoleStatsRecord
    seller: RoleStatsRecord
    mean_turns: float | None
    rejected_actions: int
    api_errors: int
    cost_usd: float


class PairingRecord(TypedDict):
    buyer_model: str
    seller_model: str
    games: int
    deals: int
    mean_buyer_score: float | None
    mean_seller_score: float | None


class SummaryRecord(TypedDict):
    schema_version: int
    run_id: str
    status: RunStatus
    updated_at: str
    finished_at: str | None
    completed_games: int
    total_games: int
    cost_usd: float
    leaderboard: list[ModelStatsRecord]
    pairings: list[PairingRecord]
