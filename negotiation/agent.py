import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Protocol

from openai import APIError, AsyncOpenAI, omit
from openai.types import CompletionUsage
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessage,
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
)
from openai.types.shared_params import FunctionParameters

from negotiation.game import Action, ActionKind
from negotiation.records import UsageRecord
from negotiation.settings import MatchSettings

PRICE_PARAMETERS: FunctionParameters = {
    "type": "object",
    "properties": {"price": {"type": "integer", "description": "Price in whole US dollars"}},
    "required": ["price"],
}

TOOLS: list[ChatCompletionToolParam] = [
    {
        "type": "function",
        "function": {
            "name": ActionKind.PROPOSE.value,
            "description": "Set your standing offer to this price, replacing any earlier offer.",
            "parameters": PRICE_PARAMETERS,
        },
    },
    {
        "type": "function",
        "function": {
            "name": ActionKind.ACCEPT.value,
            "description": "Accept the other side's latest standing offer. The price must match it.",
            "parameters": PRICE_PARAMETERS,
        },
    },
    {
        "type": "function",
        "function": {
            "name": ActionKind.END.value,
            "description": "Ask to end the negotiation. It ends once both sides have asked.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

RETRYABLE_ERRORS = (APIError, IndexError, AttributeError, TypeError)


def empty_usage() -> UsageRecord:
    return {"prompt_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0, "cost_usd": 0.0}


@dataclass
class ModelReply:
    text: str
    actions: list[Action]
    parse_problems: list[str] = field(default_factory=list[str])
    raw_tool_calls: list[dict[str, str]] = field(default_factory=list[dict[str, str]])
    reasoning: str | None = None
    provider: str | None = None
    usage: UsageRecord = field(default_factory=empty_usage)
    latency_seconds: float = 0.0
    error: str | None = None


class Negotiator(Protocol):
    async def take_turn(
        self, model: str, messages: list[ChatCompletionMessageParam]
    ) -> ModelReply: ...


def parse_price(arguments: str) -> int | None:
    try:
        value = json.loads(arguments or "{}").get("price")
    except (json.JSONDecodeError, AttributeError):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        digits = value.strip().lstrip("$").replace(",", "")
        return int(digits) if digits.isdigit() else None
    return None


def parse_tool_call(name: str, arguments: str) -> tuple[Action | None, str | None]:
    try:
        kind = ActionKind(name)
    except ValueError:
        return None, f"unknown tool {name!r}"
    if kind is ActionKind.END:
        return Action(kind), None
    price = parse_price(arguments)
    if price is None:
        return None, f"{name} needs a whole-dollar price, got {arguments!r}"
    return Action(kind, price), None


def _usage_from(raw_usage: CompletionUsage | None) -> UsageRecord:
    if raw_usage is None:
        return empty_usage()
    details = raw_usage.completion_tokens_details
    cost = (raw_usage.model_extra or {}).get("cost")
    return {
        "prompt_tokens": raw_usage.prompt_tokens,
        "completion_tokens": raw_usage.completion_tokens,
        "reasoning_tokens": (details.reasoning_tokens if details else None) or 0,
        "cost_usd": float(cost) if isinstance(cost, int | float) else 0.0,
    }


def _reasoning_from(message: ChatCompletionMessage) -> str | None:
    reasoning = (message.model_extra or {}).get("reasoning")
    return reasoning.strip() if isinstance(reasoning, str) and reasoning.strip() else None


def reply_from_completion(response: ChatCompletion, latency: float) -> ModelReply:
    message = response.choices[0].message
    reply = ModelReply(
        text=(message.content or "").strip(),
        actions=[],
        reasoning=_reasoning_from(message),
        provider=(response.model_extra or {}).get("provider"),
        usage=_usage_from(response.usage),
        latency_seconds=latency,
    )
    for call in message.tool_calls or []:
        if call.type != "function":
            continue
        name, arguments = call.function.name, call.function.arguments
        reply.raw_tool_calls.append({"name": name, "arguments": arguments})
        action, problem = parse_tool_call(name, arguments)
        if action:
            reply.actions.append(action)
        if problem:
            reply.parse_problems.append(problem)
    return reply


class OpenRouterNegotiator:
    def __init__(self, api_key: str, base_url: str, settings: MatchSettings):
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._settings = settings

    async def take_turn(self, model: str, messages: list[ChatCompletionMessageParam]) -> ModelReply:
        last_error = "no attempts made"
        for attempt in range(self._settings.request_attempts):
            try:
                return await self._request(model, messages)
            except RETRYABLE_ERRORS as error:
                last_error = f"{type(error).__name__}: {error}"
                await asyncio.sleep(2**attempt)
        return ModelReply(text="", actions=[], error=last_error)

    async def _request(self, model: str, messages: list[ChatCompletionMessageParam]) -> ModelReply:
        temperature = self._settings.temperature
        started = time.monotonic()
        response = await self._client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            max_tokens=self._settings.max_output_tokens,
            temperature=omit if temperature is None else temperature,
            extra_body={"usage": {"include": True}},
        )
        return reply_from_completion(response, time.monotonic() - started)
