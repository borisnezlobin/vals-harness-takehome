import type { RoleName, ScenarioRecord } from "./types";

export type PriceScale = {
  min: number;
  max: number;
  position: (price: number) => number;
};

const PADDING_SHARE = 0.35;

export function limitsOf(scenario: ScenarioRecord): { low: number; high: number } {
  return {
    low: Math.min(scenario.seller_minimum, scenario.buyer_maximum),
    high: Math.max(scenario.seller_minimum, scenario.buyer_maximum),
  };
}

export function priceScale(scenario: ScenarioRecord, extraPrices: number[] = []): PriceScale {
  const { low, high } = limitsOf(scenario);
  const spread = Math.max(high - low, scenario.reference_price * 0.05);
  const prices = [low - spread * PADDING_SHARE, high + spread * PADDING_SHARE, ...extraPrices];
  const min = Math.max(0, Math.min(...prices));
  const max = Math.max(...prices);
  const span = max - min || 1;
  return { min, max, position: (price) => (price - min) / span };
}

export function sellerShareOfSplit(price: number, scenario: ScenarioRecord): number {
  const { low, high } = limitsOf(scenario);
  if (high === low) return 0.5;
  return (price - low) / (high - low);
}

export function shareOfSplit(role: RoleName, price: number, scenario: ScenarioRecord): number {
  const sellerShare = sellerShareOfSplit(price, scenario);
  return role === "seller" ? sellerShare : 1 - sellerShare;
}

export function winnerOf(price: number | null, scenario: ScenarioRecord): RoleName | "even" | null {
  if (price === null) return null;
  const share = sellerShareOfSplit(price, scenario);
  if (Math.abs(share - 0.5) < 0.02) return "even";
  return share > 0.5 ? "seller" : "buyer";
}
