from dataclasses import dataclass

from openai.types.chat import ChatCompletionMessageParam

from negotiation.agent import ModelReply, Negotiator, empty_usage
from negotiation.game import ActionResult, NegotiationState
from negotiation.prompts import opening_message, opponent_turn_message, status_block, system_prompt
from negotiation.records import (
    SCHEMA_VERSION,
    GameRecord,
    OutcomeRecord,
    TurnRecord,
    UsageRecord,
)
from negotiation.roles import Role
from negotiation.scenarios import Scenario
from negotiation.scoring import score_outcome
from negotiation.settings import MatchSettings

TURN_ORDER = (Role.BUYER, Role.SELLER)


@dataclass(frozen=True)
class Matchup:
    game_id: str
    scenario: Scenario
    buyer_model: str
    seller_model: str
    repeat: int

    def model_for(self, role: Role) -> str:
        return self.buyer_model if role is Role.BUYER else self.seller_model


def summarize_actions(results: list[ActionResult]) -> str:
    if not results:
        return "none"
    parts: list[str] = []
    for result in results:
        price = "" if result.action.price is None else f"${result.action.price:,}"
        status = "" if result.accepted else " (rejected)"
        parts.append(f"{result.action.kind.value}({price}){status}")
    return ", ".join(parts)


def _problems_for(reply: ModelReply, results: list[ActionResult]) -> list[str]:
    rejected = [
        f"{result.action.kind.value}({result.action.price}) was rejected: {result.note}"
        for result in results
        if not result.accepted
    ]
    return reply.parse_problems + rejected


def total_usage(turns: list[TurnRecord]) -> UsageRecord:
    total = empty_usage()
    for turn in turns:
        total["prompt_tokens"] += turn["usage"]["prompt_tokens"]
        total["completion_tokens"] += turn["usage"]["completion_tokens"]
        total["reasoning_tokens"] += turn["usage"]["reasoning_tokens"]
        total["cost_usd"] += turn["usage"]["cost_usd"]
    return total


def _rejected_count(turn: TurnRecord) -> int:
    rejected_actions = sum(1 for action in turn["actions"] if not action["accepted"])
    return len(turn["parse_problems"]) + rejected_actions


class Negotiation:
    def __init__(self, negotiator: Negotiator, matchup: Matchup, settings: MatchSettings):
        self.negotiator = negotiator
        self.matchup = matchup
        self.settings = settings
        self.state = NegotiationState()
        self.turns_left = {role: settings.turns_per_side for role in Role}
        self.histories: dict[Role, list[ChatCompletionMessageParam]] = {
            role: [{"role": "system", "content": system_prompt(role, matchup.scenario, settings)}]
            for role in Role
        }
        self.pending_inbox = {Role.BUYER: opening_message(), Role.SELLER: ""}
        self.pending_problems: dict[Role, list[str]] = {role: [] for role in Role}
        self.last_action_summary: dict[Role, str | None] = {role: None for role in Role}
        self.turn_records: list[TurnRecord] = []

    async def run(self) -> GameRecord:
        for _ in range(self.settings.turns_per_side):
            for role in TURN_ORDER:
                await self._play_turn(role)
                if self.state.ended_by_agreement:
                    return self._result()
        return self._result()

    def _turn_prompt(self, role: Role) -> str:
        status = status_block(
            role,
            self.state,
            self.turns_left,
            self.last_action_summary[role],
            self.pending_problems[role],
        )
        return f"{self.pending_inbox[role]}\n\n{status}".strip()

    async def _play_turn(self, role: Role) -> None:
        self.histories[role].append({"role": "user", "content": self._turn_prompt(role)})
        reply = await self.negotiator.take_turn(self.matchup.model_for(role), self.histories[role])
        delivered_text = reply.text[: self.settings.message_char_limit]
        results = self.state.apply_turn(role, reply.actions)
        self.turns_left[role] -= 1
        summary = summarize_actions(results)
        self.histories[role].append(
            {"role": "assistant", "content": delivered_text or "(no message)"}
        )
        self.last_action_summary[role] = summary
        self.pending_inbox[role.opponent] = opponent_turn_message(role, delivered_text, summary)
        self.pending_problems[role] = _problems_for(reply, results)
        self.turn_records.append(self._turn_record(role, reply, delivered_text, results))

    def _turn_record(
        self, role: Role, reply: ModelReply, delivered_text: str, results: list[ActionResult]
    ) -> TurnRecord:
        return {
            "index": len(self.turn_records) + 1,
            "role": role.record_name,
            "model": self.matchup.model_for(role),
            "provider": reply.provider,
            "text": delivered_text,
            "truncated": len(reply.text) > len(delivered_text),
            "original_length": len(reply.text),
            "reasoning": reply.reasoning,
            "actions": [result.to_record() for result in results],
            "parse_problems": reply.parse_problems,
            "raw_tool_calls": reply.raw_tool_calls,
            "standing_offers": {
                "buyer": self.state.standing_offers[Role.BUYER],
                "seller": self.state.standing_offers[Role.SELLER],
            },
            "deal_after_turn": self.state.deal.price if self.state.deal else None,
            "usage": reply.usage,
            "latency_seconds": round(reply.latency_seconds, 2),
            "error": reply.error,
        }

    def _outcome(self) -> OutcomeRecord:
        deal = self.state.deal
        return {
            "deal_price": deal.price if deal else None,
            "deal_accepted_by": deal.accepted_by.record_name if deal else None,
            "ended_by_agreement": self.state.ended_by_agreement,
            "turns_played": len(self.turn_records),
            "api_errors": sum(1 for turn in self.turn_records if turn["error"]),
            "rejected_actions": sum(_rejected_count(turn) for turn in self.turn_records),
        }

    def _result(self) -> GameRecord:
        scenario = self.matchup.scenario
        outcome = self._outcome()
        deal_price = outcome["deal_price"]
        max_penalty = self.settings.max_penalty
        return {
            "schema_version": SCHEMA_VERSION,
            "game_id": self.matchup.game_id,
            "repeat": self.matchup.repeat,
            "scenario": scenario.to_record(),
            "models": {"buyer": self.matchup.buyer_model, "seller": self.matchup.seller_model},
            "outcome": outcome,
            "scores": {
                "buyer": score_outcome(Role.BUYER, deal_price, scenario, max_penalty),
                "seller": score_outcome(Role.SELLER, deal_price, scenario, max_penalty),
            },
            "usage": total_usage(self.turn_records),
            "turns": self.turn_records,
        }


async def run_negotiation(
    negotiator: Negotiator, matchup: Matchup, settings: MatchSettings
) -> GameRecord:
    return await Negotiation(negotiator, matchup, settings).run()
