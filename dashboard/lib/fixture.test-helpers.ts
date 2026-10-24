import { readFileSync } from "node:fs";
import path from "node:path";

import { parseGamesJsonl } from "./parse";
import type { GameRecord, RunConfigRecord, SummaryRecord } from "./types";

const FIXTURE_RUN = path.join(__dirname, "..", "tests", "fixtures", "runs", "20261023-164113");

export function fixtureGames(): GameRecord[] {
  return parseGamesJsonl(readFileSync(path.join(FIXTURE_RUN, "games.jsonl"), "utf8"));
}

export function fixtureConfig(): RunConfigRecord {
  return JSON.parse(readFileSync(path.join(FIXTURE_RUN, "config.json"), "utf8"));
}

export function fixtureSummary(): SummaryRecord {
  return JSON.parse(readFileSync(path.join(FIXTURE_RUN, "summary.json"), "utf8"));
}
