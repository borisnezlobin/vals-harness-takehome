import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { connection } from "next/server";

import { isSafeId, parseGamesJsonl } from "./parse";
import type { GameRecord, RunConfigRecord, RunOverview, SummaryRecord } from "./types";

export function runsDirectory(): string {
  return path.resolve(
    /*turbopackIgnore: true*/ process.env.RUNS_DIR ?? path.join(process.cwd(), "..", "runs"),
  );
}

async function readJson<T>(filePath: string): Promise<T | null> {
  try {
    return JSON.parse(await readFile(filePath, "utf8")) as T;
  } catch {
    return null;
  }
}

async function readRun(runId: string): Promise<RunOverview | null> {
  if (!isSafeId(runId)) return null;
  const directory = path.join(/*turbopackIgnore: true*/ runsDirectory(), runId);
  const [config, summary] = await Promise.all([
    readJson<RunConfigRecord>(path.join(directory, "config.json")),
    readJson<SummaryRecord>(path.join(directory, "summary.json")),
  ]);
  return config && summary ? { config, summary } : null;
}

export async function listRuns(): Promise<RunOverview[]> {
  await connection();
  let entries: string[];
  try {
    entries = await readdir(/*turbopackIgnore: true*/ runsDirectory());
  } catch {
    return [];
  }
  const runs = await Promise.all(entries.sort().reverse().map(readRun));
  return runs.filter((run): run is RunOverview => run !== null);
}

export async function getRun(runId: string): Promise<RunOverview | null> {
  await connection();
  return readRun(runId);
}

export async function getGames(runId: string): Promise<GameRecord[]> {
  await connection();
  if (!isSafeId(runId)) return [];
  try {
    const file = path.join(/*turbopackIgnore: true*/ runsDirectory(), runId, "games.jsonl");
    const text = await readFile(file, "utf8");
    return parseGamesJsonl(text);
  } catch {
    return [];
  }
}

export async function getGame(runId: string, gameId: string): Promise<GameRecord | null> {
  if (!isSafeId(gameId)) return null;
  const games = await getGames(runId);
  return games.find((game) => game.game_id === gameId) ?? null;
}
