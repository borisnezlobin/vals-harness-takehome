import type { GameRecord } from "./types";

const SAFE_ID = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;

export function isSafeId(id: string): boolean {
  return SAFE_ID.test(id) && !id.includes("..");
}

export function parseGamesJsonl(text: string): GameRecord[] {
  const games: GameRecord[] = [];
  for (const line of text.split("\n")) {
    const game = parseLine(line);
    if (game) games.push(game);
  }
  return games;
}

function parseLine(line: string): GameRecord | null {
  if (!line.trim()) return null;
  try {
    return JSON.parse(line) as GameRecord;
  } catch {
    // The engine may be halfway through appending the last line of a live run.
    return null;
  }
}
