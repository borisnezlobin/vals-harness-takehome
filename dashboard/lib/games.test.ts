import { describe, expect, it } from "vitest";

import { fixtureConfig, fixtureGames } from "./fixture.test-helpers";
import { groupByScenario, headToHead, summarizeGame } from "./games";

describe("game summaries", () => {
  const config = fixtureConfig();
  const summaries = fixtureGames().map(summarizeGame);

  it("groups every game under its scenario", () => {
    const groups = groupByScenario(config.scenarios, summaries);
    expect(groups.map((group) => group.scenario.name)).toEqual(config.scenarios.map((s) => s.name));
    expect(groups.reduce((sum, group) => sum + group.games.length, 0)).toBe(summaries.length);
  });

  it("builds one head-to-head cell per ordered pair", () => {
    const cells = headToHead(config.models, summaries);
    const count = config.models.length;
    expect(cells).toHaveLength(count * (count - 1));
    expect(cells.reduce((sum, cell) => sum + cell.games, 0)).toBe(summaries.length);
    for (const cell of cells) expect(cell.buyer).not.toBe(cell.seller);
  });
});
