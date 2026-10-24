from dataclasses import dataclass, field
from enum import StrEnum

from negotiation.records import ActionName, ActionRecord
from negotiation.roles import Role


class ActionKind(StrEnum):
    PROPOSE = "propose_offer"
    ACCEPT = "accept_offer"
    END = "end_negotiation"

    @property
    def record_name(self) -> ActionName:
        return ACTION_RECORD_NAMES[self]


ACTION_RECORD_NAMES: dict[ActionKind, ActionName] = {
    ActionKind.PROPOSE: "propose_offer",
    ActionKind.ACCEPT: "accept_offer",
    ActionKind.END: "end_negotiation",
}


@dataclass(frozen=True)
class Action:
    kind: ActionKind
    price: int | None = None


@dataclass(frozen=True)
class ActionResult:
    action: Action
    accepted: bool
    note: str

    def to_record(self) -> ActionRecord:
        return {
            "kind": self.action.kind.record_name,
            "price": self.action.price,
            "accepted": self.accepted,
            "note": self.note,
        }


@dataclass(frozen=True)
class Deal:
    price: int
    accepted_by: Role


def _empty_offers() -> dict[Role, int | None]:
    return {Role.BUYER: None, Role.SELLER: None}


def _no_end_requests() -> dict[Role, bool]:
    return {Role.BUYER: False, Role.SELLER: False}


@dataclass
class NegotiationState:
    standing_offers: dict[Role, int | None] = field(default_factory=_empty_offers)
    deal: Deal | None = None
    end_requested: dict[Role, bool] = field(default_factory=_no_end_requests)

    @property
    def ended_by_agreement(self) -> bool:
        return all(self.end_requested.values())

    def apply_turn(self, role: Role, actions: list[Action]) -> list[ActionResult]:
        results: list[ActionResult] = []
        terms_changed = False
        wants_to_end = False
        for action in actions:
            if action.kind is ActionKind.END:
                wants_to_end = True
                results.append(ActionResult(action, True, "asked to end the negotiation"))
                continue
            result, changed = self._apply_price_action(role, action)
            results.append(result)
            terms_changed = terms_changed or changed
        if terms_changed:
            self.end_requested = _no_end_requests()
        if wants_to_end:
            self.end_requested[role] = True
        return results

    def _apply_price_action(self, role: Role, action: Action) -> tuple[ActionResult, bool]:
        if action.price is None or action.price <= 0:
            return ActionResult(action, False, "price must be a positive whole number"), False
        if action.kind is ActionKind.PROPOSE:
            return self._propose(role, action)
        return self._accept(role, action)

    def _propose(self, role: Role, action: Action) -> tuple[ActionResult, bool]:
        changed = self.standing_offers[role] != action.price
        self.standing_offers[role] = action.price
        return ActionResult(action, True, f"standing offer is now ${action.price:,}"), changed

    def _accept(self, role: Role, action: Action) -> tuple[ActionResult, bool]:
        price = action.price
        opponent_offer = self.standing_offers[role.opponent]
        if opponent_offer is None:
            note = f"the {role.opponent.value} has not made an offer yet"
            return ActionResult(action, False, note), False
        if price is None or opponent_offer != price:
            note = f"the {role.opponent.value}'s latest offer is ${opponent_offer:,}, not ${action.price:,}"
            return ActionResult(action, False, note), False
        changed = self.deal is None or self.deal.price != price
        self.deal = Deal(price=price, accepted_by=role)
        return ActionResult(action, True, f"deal agreed at ${price:,}"), changed
