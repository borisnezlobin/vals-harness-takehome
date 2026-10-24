from typing import Any

import pytest
from openai.types.chat import ChatCompletion

from negotiation.agent import parse_price, parse_tool_call, reply_from_completion
from negotiation.game import ActionKind


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ('{"price": 500}', 500),
        ('{"price": 500.0}', 500),
        ('{"price": "$1,250"}', 1250),
        ('{"price": 500.5}', None),
        ('{"price": true}', None),
        ('{"price": "five hundred"}', None),
        ("{}", None),
        ("not json", None),
        ("", None),
        ("[1, 2]", None),
    ],
)
def test_parse_price(arguments: str, expected: int | None) -> None:
    assert parse_price(arguments) == expected


def test_parse_tool_call_handles_each_tool() -> None:
    assert parse_tool_call("propose_offer", '{"price": 10}')[0] is not None
    accept, _ = parse_tool_call("accept_offer", '{"price": 10}')
    assert accept is not None
    assert accept.kind is ActionKind.ACCEPT
    end, _ = parse_tool_call("end_negotiation", "")
    assert end is not None
    assert end.price is None


def test_parse_tool_call_reports_problems() -> None:
    assert parse_tool_call("walk_away", "{}") == (None, "unknown tool 'walk_away'")
    action, problem = parse_tool_call("propose_offer", '{"amount": 5}')
    assert action is None
    assert problem is not None
    assert "whole-dollar price" in problem


def _completion(message: dict[str, Any], usage: dict[str, Any] | None = None) -> ChatCompletion:
    return ChatCompletion.model_validate(
        {
            "id": "gen-1",
            "object": "chat.completion",
            "created": 0,
            "model": "test/model",
            "provider": "TestCloud",
            "choices": [{"index": 0, "finish_reason": "stop", "message": message}],
            "usage": usage,
        }
    )


def _tool_call(name: str, arguments: str) -> dict[str, Any]:
    return {"id": name, "type": "function", "function": {"name": name, "arguments": arguments}}


def test_reply_collects_text_actions_reasoning_and_cost() -> None:
    completion = _completion(
        {
            "role": "assistant",
            "content": "  Let's meet at $550.  ",
            "reasoning": "They seem keen.",
            "tool_calls": [
                _tool_call("propose_offer", '{"price": 550}'),
                _tool_call("accept_offer", '{"price": "lots"}'),
            ],
        },
        usage={
            "prompt_tokens": 100,
            "completion_tokens": 40,
            "total_tokens": 140,
            "completion_tokens_details": {"reasoning_tokens": 30},
            "cost": 0.002,
        },
    )
    reply = reply_from_completion(completion, latency=1.5)
    assert reply.text == "Let's meet at $550."
    assert reply.reasoning == "They seem keen."
    assert reply.provider == "TestCloud"
    assert [action.price for action in reply.actions] == [550]
    assert len(reply.parse_problems) == 1
    assert len(reply.raw_tool_calls) == 2
    assert reply.usage == {
        "prompt_tokens": 100,
        "completion_tokens": 40,
        "reasoning_tokens": 30,
        "cost_usd": 0.002,
    }
    assert reply.latency_seconds == 1.5


def test_reply_without_usage_or_content() -> None:
    reply = reply_from_completion(_completion({"role": "assistant", "content": None}), latency=0)
    assert reply.text == ""
    assert reply.actions == []
    assert reply.reasoning is None
    assert reply.usage["cost_usd"] == 0
