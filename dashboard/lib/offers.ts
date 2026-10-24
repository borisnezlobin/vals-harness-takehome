import type { RoleName, TurnRecord } from "./types";

export type OfferPoint = { turn: number; price: number };

export type OfferSeries = Record<RoleName, OfferPoint[]>;

export type DealPoint = { turn: number; price: number; acceptedBy: RoleName };

export function offerSeries(turns: TurnRecord[]): OfferSeries {
  const series: OfferSeries = { buyer: [], seller: [] };
  for (const turn of turns) {
    for (const role of ["buyer", "seller"] as const) {
      const price = turn.standing_offers[role];
      if (price !== null) series[role].push({ turn: turn.index, price });
    }
  }
  return series;
}

export function dealPoints(turns: TurnRecord[]): DealPoint[] {
  const deals: DealPoint[] = [];
  for (const turn of turns) {
    const accepted = turn.actions.find((action) => action.kind === "accept_offer" && action.accepted);
    if (accepted?.price != null) {
      deals.push({ turn: turn.index, price: accepted.price, acceptedBy: turn.role });
    }
  }
  return deals;
}

export function allPrices(turns: TurnRecord[]): number[] {
  const prices: number[] = [];
  for (const turn of turns) {
    for (const price of Object.values(turn.standing_offers)) {
      if (price !== null) prices.push(price);
    }
  }
  return prices;
}

export type TurnSummary = {
  offered: number | null;
  accepted: number | null;
  askedToEnd: boolean;
  rejections: string[];
};

export function summarizeTurn(turn: TurnRecord): TurnSummary {
  const summary: TurnSummary = { offered: null, accepted: null, askedToEnd: false, rejections: [] };
  for (const action of turn.actions) {
    applyAction(summary, action);
  }
  summary.rejections.push(...turn.parse_problems);
  return summary;
}

function applyAction(summary: TurnSummary, action: TurnRecord["actions"][number]): void {
  if (!action.accepted) {
    summary.rejections.push(rejectionText(action));
    return;
  }
  if (action.kind === "propose_offer") summary.offered = action.price;
  if (action.kind === "accept_offer") summary.accepted = action.price;
  if (action.kind === "end_negotiation") summary.askedToEnd = true;
}

function rejectionText(action: TurnRecord["actions"][number]): string {
  const verb = action.kind === "accept_offer" ? "Tried to accept" : "Tried to offer";
  const price = action.price === null ? "" : ` $${action.price.toLocaleString("en-US")}`;
  return `${verb}${price}, but ${action.note}`;
}
