"use client";

import type { KeyboardEvent } from "react";

import { limitsOf, priceScale } from "@/lib/corridor";
import { formatPrice, modelLabel } from "@/lib/format";
import { type OfferPoint, allPrices, dealPoints, offerSeries } from "@/lib/offers";
import { niceTicks } from "@/lib/ticks";
import type { GameRecord, RoleName, TurnRecord } from "@/lib/types";
import { useElementWidth } from "@/lib/useElementWidth";

import { ROLE_TITLE, RoleMark } from "../RoleMark";

const HEIGHT = 340;
const MARGIN = { top: 16, right: 112, bottom: 36, left: 64 };
const ROLE_STROKE: Record<RoleName, string> = { buyer: "stroke-buyer", seller: "stroke-seller" };
const ROLE_FILL: Record<RoleName, string> = { buyer: "fill-buyer", seller: "fill-seller" };

type Geometry = {
  width: number;
  x: (turn: number) => number;
  y: (price: number) => number;
  turnWidth: number;
  priceTicks: number[];
};

function geometry(game: GameRecord, width: number): Geometry {
  const turnCount = Math.max(1, game.turns.length);
  const plotWidth = Math.max(1, width - MARGIN.left - MARGIN.right);
  const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom;
  const scale = priceScale(game.scenario, allPrices(game.turns));
  const turnWidth = plotWidth / turnCount;
  return {
    width,
    turnWidth,
    x: (turn) => MARGIN.left + (turn - 0.5) * turnWidth,
    y: (price) => MARGIN.top + (1 - scale.position(price)) * plotHeight,
    priceTicks: niceTicks(scale.min, scale.max, 4),
  };
}

function stepPath(points: OfferPoint[], lastTurn: number, g: Geometry): string {
  if (points.length === 0) return "";
  const [first, ...rest] = points;
  const commands = [`M ${g.x(first.turn)} ${g.y(first.price)}`];
  for (const point of rest) {
    commands.push(`H ${g.x(point.turn)}`, `V ${g.y(point.price)}`);
  }
  commands.push(`H ${g.x(lastTurn)}`);
  return commands.join(" ");
}

function proposalsBy(role: RoleName, turns: TurnRecord[]): OfferPoint[] {
  return turns.flatMap((turn) => {
    if (turn.role !== role) return [];
    const proposal = turn.actions.find((action) => action.kind === "propose_offer" && action.accepted);
    return proposal?.price != null ? [{ turn: turn.index, price: proposal.price }] : [];
  });
}

function Zone({ game, g }: { game: GameRecord; g: Geometry }) {
  const { low, high } = limitsOf(game.scenario);
  const top = g.y(high);
  const height = g.y(low) - top;
  const zoneFill = game.scenario.reserves_overlap
    ? { className: "fill-zone" }
    : { fill: "url(#gap-hatch)" };
  return (
    <>
      <defs>
        <pattern id="gap-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="6" strokeWidth="1.5" className="stroke-line" />
        </pattern>
      </defs>
      <rect x={MARGIN.left} y={top} width={g.width - MARGIN.left - MARGIN.right} height={height} {...zoneFill} />
    </>
  );
}

const LABEL_GAP = 34;

function limitLabelOffsets(g: Geometry, game: GameRecord): Record<RoleName, number> {
  const sellerY = g.y(game.scenario.seller_minimum);
  const buyerY = g.y(game.scenario.buyer_maximum);
  const overlap = LABEL_GAP - Math.abs(sellerY - buyerY);
  if (overlap <= 0) return { buyer: 0, seller: 0 };
  const sellerBelow = sellerY >= buyerY ? 1 : -1;
  return { seller: (sellerBelow * overlap) / 2, buyer: (-sellerBelow * overlap) / 2 };
}

function LimitLine({ role, price, labelOffset, g }: { role: RoleName; price: number; labelOffset: number; g: Geometry }) {
  const y = g.y(price);
  const labelY = y + labelOffset;
  const label = role === "seller" ? "Seller’s floor" : "Buyer’s ceiling";
  return (
    <g>
      <line x1={MARGIN.left} x2={g.width - MARGIN.right} y1={y} y2={y} strokeWidth="1.5" className={ROLE_STROKE[role]} />
      <text x={g.width - MARGIN.right + 10} y={labelY - 3} className="fill-ink-secondary type-small">
        {label}
      </text>
      <text x={g.width - MARGIN.right + 10} y={labelY + 14} className="fill-ink type-number type-small">
        {formatPrice(price)}
      </text>
    </g>
  );
}

function PriceAxis({ g }: { g: Geometry }) {
  return (
    <g aria-hidden="true">
      {g.priceTicks.map((tick) => (
        <g key={tick}>
          <line x1={MARGIN.left} x2={g.width - MARGIN.right} y1={g.y(tick)} y2={g.y(tick)} className="stroke-line" strokeWidth="1" />
          <text x={MARGIN.left - 10} y={g.y(tick) + 4} textAnchor="end" className="fill-ink-muted type-number type-small">
            {formatPrice(tick)}
          </text>
        </g>
      ))}
    </g>
  );
}

function TurnAxis({ game, g }: { game: GameRecord; g: Geometry }) {
  const step = g.turnWidth < 28 ? 2 : 1;
  return (
    <g aria-hidden="true">
      {game.turns
        .filter((turn) => (turn.index - 1) % step === 0)
        .map((turn) => (
          <text key={turn.index} x={g.x(turn.index)} y={HEIGHT - 12} textAnchor="middle" className="fill-ink-muted type-number type-small">
            {turn.index}
          </text>
        ))}
    </g>
  );
}

function RevealClip({ g }: { g: Geometry }) {
  return (
    <defs>
      <clipPath id="offer-reveal">
        <rect x={MARGIN.left - 12} y={0} width={g.width - MARGIN.left - MARGIN.right + 24} height={HEIGHT} className="animate-reveal" />
      </clipPath>
    </defs>
  );
}

function OfferLines({ game, g }: { game: GameRecord; g: Geometry }) {
  const series = offerSeries(game.turns);
  const lastTurn = game.turns.length;
  return (
    <g clipPath="url(#offer-reveal)">
      <RevealClip g={g} />
      {(["buyer", "seller"] as const).map((role) => (
        <g key={role}>
          <path
            d={stepPath(series[role], lastTurn, g)}
            fill="none"
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
            className={ROLE_STROKE[role]}
          />
          {proposalsBy(role, game.turns).map((point) => (
            <circle
              key={point.turn}
              cx={g.x(point.turn)}
              cy={g.y(point.price)}
              r="4.5"
              strokeWidth="2"
              className={`${ROLE_FILL[role]} stroke-surface`}
            />
          ))}
        </g>
      ))}
    </g>
  );
}

function DealMarks({ game, g }: { game: GameRecord; g: Geometry }) {
  const deals = dealPoints(game.turns);
  const finalPrice = game.outcome.deal_price;
  return (
    <g>
      {deals.map((deal, index) => {
        const isFinal = index === deals.length - 1 && deal.price === finalPrice;
        return (
          <g key={`${deal.turn}-${deal.price}`} className={isFinal ? "animate-settle" : undefined}>
            <circle cx={g.x(deal.turn)} cy={g.y(deal.price)} r={isFinal ? 7 : 5} strokeWidth="2.5" className="fill-ink stroke-surface" />
          </g>
        );
      })}
    </g>
  );
}

function Crosshair({ turn, g }: { turn: number; g: Geometry }) {
  return (
    <line
      x1={g.x(turn)}
      x2={g.x(turn)}
      y1={MARGIN.top}
      y2={HEIGHT - MARGIN.bottom}
      strokeWidth="1"
      className="stroke-ink-muted"
    />
  );
}

function TurnTooltip({ turn, g }: { turn: TurnRecord; g: Geometry }) {
  const flip = g.x(turn.index) > g.width - MARGIN.right - 180;
  const left = flip ? g.x(turn.index) - 12 : g.x(turn.index) + 12;
  return (
    <div
      className="pointer-events-none absolute top-4 z-10 flex w-52 flex-col gap-1.5 rounded-md bg-surface p-3 shadow-floating"
      style={{ left, transform: flip ? "translateX(-100%)" : undefined }}
    >
      <span className="inline-flex items-center gap-1.5 type-small">
        <RoleMark role={turn.role} />
        Turn {turn.index}, {modelLabel(turn.model)}
      </span>
      {(["buyer", "seller"] as const).map((role) => (
        <span key={role} className="flex justify-between type-small text-ink-secondary">
          <span className="inline-flex items-center gap-1.5">
            <RoleMark role={role} />
            {ROLE_TITLE[role]} offer
          </span>
          <span className="type-number text-ink">{formatPrice(turn.standing_offers[role])}</span>
        </span>
      ))}
      {turn.deal_after_turn !== null && (
        <span className="flex justify-between type-small text-ink-secondary">
          <span className="inline-flex items-center gap-1.5">
            <span className="size-2.5 rounded-full bg-ink" aria-hidden="true" />
            Deal locked in
          </span>
          <span className="type-number text-ink">{formatPrice(turn.deal_after_turn)}</span>
        </span>
      )}
    </div>
  );
}

function HitAreas({
  game,
  g,
  onHover,
  onSelect,
}: {
  game: GameRecord;
  g: Geometry;
  onHover: (turn: number | null) => void;
  onSelect: (turn: number) => void;
}) {
  return (
    <g onPointerLeave={() => onHover(null)}>
      {game.turns.map((turn) => (
        <rect
          key={turn.index}
          x={g.x(turn.index) - g.turnWidth / 2}
          y={MARGIN.top}
          width={g.turnWidth}
          height={HEIGHT - MARGIN.top - MARGIN.bottom}
          fill="transparent"
          className="cursor-pointer"
          onPointerMove={(event) => {
            if (event.pointerType === "mouse") onHover(turn.index);
          }}
          onClick={() => onSelect(turn.index)}
        />
      ))}
    </g>
  );
}

function chartSummary(game: GameRecord): string {
  const price = game.outcome.deal_price;
  const ending = price === null ? "ended with no deal" : `ended with a deal at ${formatPrice(price)}`;
  return `Offers over ${game.turns.length} turns. The negotiation ${ending}. Use the left and right arrow keys to step through turns.`;
}

export function OfferChart({
  game,
  activeTurn,
  selectedTurn,
  onHover,
  onSelect,
}: {
  game: GameRecord;
  activeTurn: number | null;
  selectedTurn: number | null;
  onHover: (turn: number | null) => void;
  onSelect: (turn: number) => void;
}) {
  const [ref, width] = useElementWidth<HTMLDivElement>();
  const g = geometry(game, width);
  const active = activeTurn === null ? null : game.turns[activeTurn - 1];
  const labelOffsets = limitLabelOffsets(g, game);

  function handleKey(event: KeyboardEvent<HTMLDivElement>) {
    const delta = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
    if (!delta) return;
    event.preventDefault();
    const next = Math.min(game.turns.length, Math.max(1, (selectedTurn ?? 0) + delta));
    onSelect(next);
  }

  return (
    <div
      ref={ref}
      role="group"
      tabIndex={0}
      aria-label={chartSummary(game)}
      onKeyDown={handleKey}
      className="focus-ring relative rounded-md"
      style={{ height: HEIGHT }}
    >
      {width > 0 && (
        <svg width={width} height={HEIGHT} className="overflow-visible">
          <Zone game={game} g={g} />
          <PriceAxis g={g} />
          <LimitLine role="seller" price={game.scenario.seller_minimum} labelOffset={labelOffsets.seller} g={g} />
          <LimitLine role="buyer" price={game.scenario.buyer_maximum} labelOffset={labelOffsets.buyer} g={g} />
          {active && <Crosshair turn={active.index} g={g} />}
          <OfferLines game={game} g={g} />
          <DealMarks game={game} g={g} />
          <TurnAxis game={game} g={g} />
          <HitAreas game={game} g={g} onHover={onHover} onSelect={onSelect} />
        </svg>
      )}
      {active && width > 0 && <TurnTooltip turn={active} g={g} />}
    </div>
  );
}
