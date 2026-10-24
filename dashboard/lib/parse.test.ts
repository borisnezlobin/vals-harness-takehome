import { describe, expect, it } from "vitest";

import { fixtureConfig, fixtureGames, fixtureSummary } from "./fixture.test-helpers";
import { isSafeId, parseGamesJsonl } from "./parse";
import { SCHEMA_VERSION } from "./types";

describe("isSafeId", () => {
  it.each(["20261023-164113", "used-car--openai_gpt-oss-120b--vs--x--r0"])("accepts %s", (id) => {
    expect(isSafeId(id)).toBe(true);
  });

  it.each(["", "..", "../etc", "a/b", "a\\b", ".hidden", "a..b"])("rejects %s", (id) => {
    expect(isSafeId(id)).toBe(false);
  });
});

describe("parseGamesJsonl", () => {
  it("skips blank lines and a half-written last line", () => {
    const text = '{"game_id":"a"}\n\n{"game_id":"b"}\n{"game_id":"c';
    expect(parseGamesJsonl(text).map((game) => game.game_id)).toEqual(["a", "b"]);
  });
});

describe("fixture written by the Python engine", () => {
  it("matches the dashboard schema version", () => {
    expect(fixtureConfig().schema_version).toBe(SCHEMA_VERSION);
    expect(fixtureSummary().schema_version).toBe(SCHEMA_VERSION);
    for (const game of fixtureGames()) expect(game.schema_version).toBe(SCHEMA_VERSION);
  });

  it("has every field the dashboard reads", () => {
    const [game] = fixtureGames();
    expect(Object.keys(game).sort()).toEqual(
      ["game_id", "models", "outcome", "repeat", "schema_version", "scenario", "scores", "turns", "usage"].sort(),
    );
    expect(Object.keys(game.turns[0]).sort()).toEqual(
      [
        "actions",
        "deal_after_turn",
        "error",
        "index",
        "latency_seconds",
        "model",
        "original_length",
        "parse_problems",
        "provider",
        "raw_tool_calls",
        "reasoning",
        "role",
        "standing_offers",
        "text",
        "truncated",
        "usage",
      ].sort(),
    );
  });
});
