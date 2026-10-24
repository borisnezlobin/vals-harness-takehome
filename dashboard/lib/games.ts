import { sellerShareOfSplit } from "./corridor";
import type { GameRecord, RoleName, ScenarioRecord } from "./types";

export type GameSummary = {
  gameId: string;
  scenario: ScenarioRecord;
  models: Record<RoleName, string>;
  dealPrice: number | null;
  scores: Record<RoleName, number>;
  turnsPlayed: number;
  endedByAgreement: boolean;
  rejectedActions: number;
};

export function summarizeGame(game: GameRecord): GameSummary {
  return {
    gameId: game.game_id,
    scenario: game.scenario,
    models: game.models,
    dealPrice: game.outcome.deal_price,
    scores: game.scores,
    turnsPlayed: game.outcome.turns_played,
    endedByAgreement: game.outcome.ended_by_agreement,
    rejectedActions: game.outcome.rejected_actions,
  };
}

export type ScenarioGroup = { scenario: ScenarioRecord; games: GameSummary[] };

export function groupByScenario(
  scenarios: ScenarioRecord[],
  games: GameSummary[],
): ScenarioGroup[] {
  return scenarios.map((scenario) => ({
    scenario,
    games: games
      .filter((game) => game.scenario.name === scenario.name)
      .sort((a, b) => a.gameId.localeCompare(b.gameId)),
  }));
}

export type HeadToHead = {
  buyer: string;
  seller: string;
  games: number;
  deals: number;
  meanSellerShare: number | null;
  meanBuyerScore: number | null;
  meanSellerScore: number | null;
};

function mean(values: number[]): number | null {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}

export function headToHead(models: string[], games: GameSummary[]): HeadToHead[] {
  const cells: HeadToHead[] = [];
  for (const buyer of models) {
    for (const seller of models) {
      if (buyer === seller) continue;
      cells.push(headToHeadCell(buyer, seller, games));
    }
  }
  return cells;
}

function headToHeadCell(buyer: string, seller: string, games: GameSummary[]): HeadToHead {
  const played = games.filter((game) => game.models.buyer === buyer && game.models.seller === seller);
  const shares: number[] = [];
  for (const game of played) {
    if (game.dealPrice !== null) shares.push(sellerShareOfSplit(game.dealPrice, game.scenario));
  }
  return {
    buyer,
    seller,
    games: played.length,
    deals: shares.length,
    meanSellerShare: mean(shares),
    meanBuyerScore: mean(played.map((game) => game.scores.buyer)),
    meanSellerScore: mean(played.map((game) => game.scores.seller)),
  };
}
