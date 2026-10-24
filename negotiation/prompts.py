from negotiation.game import Deal, NegotiationState
from negotiation.roles import Role
from negotiation.scenarios import Scenario
from negotiation.settings import MatchSettings


def _reserve_sentence(role: Role, scenario: Scenario) -> str:
    if role is Role.SELLER:
        return (
            f"Your minimum acceptable price is ${scenario.seller_minimum:,}. "
            "Every dollar above it is profit for you."
        )
    return (
        f"Your maximum budget is ${scenario.buyer_maximum:,}. "
        "Every dollar below it is savings for you."
    )


def _goal_sentence(role: Role) -> str:
    if role is Role.SELLER:
        return "Your goal is to sell for as high a price as you can."
    return "Your goal is to buy for as low a price as you can."


def system_prompt(role: Role, scenario: Scenario, settings: MatchSettings) -> str:
    opponent = role.opponent.value
    return f"""You are the {role.value} in a price negotiation for {scenario.item}.

{_reserve_sentence(role, scenario)} {_goal_sentence(role)} The {opponent} has their own private limit, and you don't know it. Their limit might not even overlap with yours.

How you are scored:
- If a deal is reached, your score is how far the final price lands on your side of your own limit, measured as a percentage of the item's price. A deal past your limit gives you a negative score. Small losses cost you roughly what they look like, while very large losses flatten out toward a fixed worst score.
- If no deal is reached, you get that worst possible score. Any deal, even a bad one, scores better than no deal at all.

How the negotiation works:
- The buyer speaks first, and then you take turns. Each side gets {settings.turns_per_side} turns, and the turn count is shown to you every turn.
- On each turn you may write a message to the {opponent}. Only the first {settings.message_char_limit:,} characters are delivered, and anything longer is cut off.
- Offers, acceptances and requests to end only count when you call a tool. Writing a number in your message does not make it an offer.
- You can use these tools on any turn, and you can use more than one per turn:
  - propose_offer(price): set your standing offer to a whole-dollar price. It replaces any earlier offer of yours.
  - accept_offer(price): accept the {opponent}'s latest standing offer. The price must match it exactly. Accepting locks in a deal at that price, but the negotiation keeps going. If a different offer is accepted later, the newer deal replaces the old one.
  - end_negotiation(): say you're ready to stop. The negotiation ends early only once both sides have asked to end, with no new offer or acceptance in between. Otherwise it runs until both sides have used all their turns.
- The final price is whatever deal is locked in when the negotiation ends. If nothing has been accepted by then, there is no deal."""


def _offer_text(price: int | None) -> str:
    return "none" if price is None else f"${price:,}"


def _deal_text(deal: Deal | None, role: Role) -> str:
    if deal is None:
        return "none yet"
    accepter = "you" if deal.accepted_by is role else f"the {role.opponent.value}"
    return f"${deal.price:,} (accepted by {accepter})"


def status_block(
    role: Role,
    state: NegotiationState,
    turns_left: dict[Role, int],
    your_last_actions: str | None,
    problems: list[str],
) -> str:
    opponent = role.opponent
    lines = [
        "Current status:",
        f"- This is your turn. Turns you have left, including this one: {turns_left[role]}",
        f"- Turns the {opponent.value} has left after this: {turns_left[opponent]}",
        f"- Your standing offer: {_offer_text(state.standing_offers[role])}",
        f"- The {opponent.value}'s standing offer: {_offer_text(state.standing_offers[opponent])}",
        f"- Locked-in deal: {_deal_text(state.deal, role)}",
        f"- The {opponent.value} has asked to end: {'yes' if state.end_requested[opponent] else 'no'}",
    ]
    if your_last_actions is not None:
        lines.append(f"- Tools you called last turn: {your_last_actions}")
    if problems:
        lines.append("- Problems with your last turn: " + "; ".join(problems))
    return "\n".join(lines)


def opening_message() -> str:
    return "The negotiation is starting, and you speak first."


def opponent_turn_message(opponent: Role, text: str, action_summary: str) -> str:
    spoken = text if text else "(no message)"
    return (
        f"The {opponent.value} said:\n{spoken}\n\nThe {opponent.value}'s actions: {action_summary}"
    )
