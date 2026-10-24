import { describe, expect, it } from "vitest";

import { fixtureGames } from "./fixture.test-helpers";
import { allPrices, dealPoints, offerSeries, summarizeTurn } from "./offers";
import type { TurnRecord } from "./types";

function turn(overrides: Partial<TurnRecord>): TurnRecord {
  return {
    index: 1,
    role: "buyer",
    model: "m",
    provider: null,
    text: "",
    truncated: false,
    original_length: 0,
    reasoning: null,
    actions: [],
    parse_problems: [],
    raw_tool_calls: [],
    standing_offers: { buyer: null, seller: null },
    deal_after_turn: null,
    usage: { prompt_tokens: 0, completion_tokens: 0, reasoning_tokens: 0, cost_usd: 0 },
    latency_seconds: 0,
    error: null,
    ...overrides,
  };
}

describe("offer series", () => {
  it("tracks each side's standing offer per turn", () => {
    const turns = [
      turn({ index: 1, standing_offers: { buyer: 400, seller: null } }),
      turn({ index: 2, role: "seller", standing_offers: { buyer: 400, seller: 700 } }),
    ];
    expect(offerSeries(turns)).toEqual({
      buyer: [
        { turn: 1, price: 400 },
        { turn: 2, price: 400 },
      ],
      seller: [{ turn: 2, price: 700 }],
    });
    expect(allPrices(turns)).toEqual([400, 400, 700]);
  });

  it("finds accepted deals", () => {
    const turns = [
      turn({
        index: 2,
        role: "seller",
        actions: [
          { kind: "accept_offer", price: 450, accepted: false, note: "no" },
          { kind: "accept_offer", price: 400, accepted: true, note: "ok" },
        ],
      }),
    ];
    expect(dealPoints(turns)).toEqual([{ turn: 2, price: 400, acceptedBy: "seller" }]);
  });

  it("summarizes a turn's actions and problems", () => {
    const summary = summarizeTurn(
      turn({
        actions: [
          { kind: "propose_offer", price: 450, accepted: true, note: "" },
          { kind: "end_negotiation", price: null, accepted: true, note: "" },
          { kind: "accept_offer", price: 999, accepted: false, note: "the seller's latest offer is $700" },
        ],
        parse_problems: ["unknown tool 'walk'"],
      }),
    );
    expect(summary.offered).toBe(450);
    expect(summary.askedToEnd).toBe(true);
    expect(summary.rejections).toEqual([
      "Tried to accept $999, but the seller's latest offer is $700",
      "unknown tool 'walk'",
    ]);
  });

  it("ends every fixture game on its last accepted offer", () => {
    for (const game of fixtureGames()) {
      const deals = dealPoints(game.turns);
      const last = deals.at(-1)?.price ?? null;
      expect(last).toBe(game.outcome.deal_price);
    }
  });
});
