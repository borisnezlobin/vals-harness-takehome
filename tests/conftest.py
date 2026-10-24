from collections.abc import Callable

import pytest
from openai.types.chat import ChatCompletionMessageParam

from negotiation.agent import ModelReply
from negotiation.game import Action, ActionKind
from negotiation.scenarios import Scenario

ReplyFactory = Callable[[str, list[ChatCompletionMessageParam]], ModelReply]


class ScriptedNegotiator:
    def __init__(self, reply_for: ReplyFactory):
        self.reply_for = reply_for
        self.calls: list[tuple[str, list[ChatCompletionMessageParam]]] = []

    async def take_turn(self, model: str, messages: list[ChatCompletionMessageParam]) -> ModelReply:
        self.calls.append((model, list(messages)))
        return self.reply_for(model, messages)


def propose(price: int) -> Action:
    return Action(ActionKind.PROPOSE, price)


def accept(price: int) -> Action:
    return Action(ActionKind.ACCEPT, price)


def end() -> Action:
    return Action(ActionKind.END)


def reply(*actions: Action, text: str = "") -> ModelReply:
    return ModelReply(text=text, actions=list(actions))


@pytest.fixture
def car() -> Scenario:
    return Scenario(name="car", item="a car", seller_minimum=500, buyer_maximum=600)


@pytest.fixture
def no_overlap_car() -> Scenario:
    return Scenario(name="car-gap", item="a car", seller_minimum=600, buyer_maximum=500)
