import type { CSSProperties, ReactNode } from "react";

import { type PriceScale, limitsOf, priceScale } from "@/lib/corridor";
import { formatPrice } from "@/lib/format";
import type { ScenarioRecord } from "@/lib/types";

type CorridorProps = {
  scenario: ScenarioRecord;
  price: number | null;
  scale?: PriceScale;
  size?: "strip" | "hero";
  animate?: boolean;
};

function percent(value: number): string {
  return `${Math.min(100, Math.max(0, value * 100)).toFixed(2)}%`;
}

const HATCH: CSSProperties = {
  backgroundImage:
    "repeating-linear-gradient(135deg, var(--color-line) 0 1.5px, transparent 1.5px 6px)",
};

function Zone({ scenario, scale }: { scenario: ScenarioRecord; scale: PriceScale }) {
  const { low, high } = limitsOf(scenario);
  const left = scale.position(low);
  const width = scale.position(high) - left;
  const style: CSSProperties = { left: percent(left), width: percent(width) };
  if (scenario.reserves_overlap) {
    return <div className="absolute inset-y-0 rounded-sm bg-zone" style={style} />;
  }
  return <div className="absolute inset-y-0" style={{ ...style, ...HATCH }} />;
}

function LimitTick({ at, tone }: { at: number; tone: "buyer" | "seller" }) {
  const color = tone === "buyer" ? "bg-buyer" : "bg-seller";
  return (
    <div
      className={`absolute inset-y-0 w-0.5 -translate-x-1/2 rounded-full ${color}`}
      style={{ left: percent(at) }}
    />
  );
}

function DealDot({ at, size, animate }: { at: number; size: "strip" | "hero"; animate: boolean }) {
  const dimension = size === "hero" ? "size-4" : "size-2.5";
  return (
    <div
      className={`absolute top-1/2 -translate-x-1/2 -translate-y-1/2 ${animate ? "animate-settle" : ""}`}
      style={{ left: percent(at) }}
    >
      <div className={`${dimension} rounded-full bg-ink ring-2 ring-surface`} />
    </div>
  );
}

export function Corridor({ scenario, price, scale, size = "strip", animate = false }: CorridorProps) {
  const resolvedScale = scale ?? priceScale(scenario, price === null ? [] : [price]);
  const height = size === "hero" ? "h-6" : "h-3";
  return (
    <div className={`relative w-full ${height}`} aria-hidden="true">
      <div className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-line" />
      <Zone scenario={scenario} scale={resolvedScale} />
      <LimitTick at={resolvedScale.position(scenario.seller_minimum)} tone="seller" />
      <LimitTick at={resolvedScale.position(scenario.buyer_maximum)} tone="buyer" />
      {price !== null && (
        <DealDot at={resolvedScale.position(price)} size={size} animate={animate} />
      )}
    </div>
  );
}

export function corridorDescription(scenario: ScenarioRecord, price: number | null): string {
  const limits = `seller's floor ${formatPrice(scenario.seller_minimum)}, buyer's ceiling ${formatPrice(scenario.buyer_maximum)}`;
  return price === null ? `No deal; ${limits}` : `Deal at ${formatPrice(price)}; ${limits}`;
}

function anchorClass(position: number): string {
  if (position < 0.12) return "translate-x-0 text-left";
  if (position > 0.88) return "-translate-x-full text-right";
  return "-translate-x-1/2 text-center";
}

function PositionedLabel({ at, children }: { at: number; children: ReactNode }) {
  return (
    <span className={`absolute whitespace-nowrap ${anchorClass(at)}`} style={{ left: percent(at) }}>
      {children}
    </span>
  );
}

export function CorridorHero({ scenario, price }: { scenario: ScenarioRecord; price: number | null }) {
  const scale = priceScale(scenario, price === null ? [] : [price]);
  return (
    <figure className="flex flex-col gap-2">
      <figcaption className="sr-only">{corridorDescription(scenario, price)}</figcaption>
      <div className="relative h-6 type-small type-number" aria-hidden="true">
        {price !== null && (
          <PositionedLabel at={scale.position(price)}>
            <span className="text-ink">Deal at {formatPrice(price)}</span>
          </PositionedLabel>
        )}
      </div>
      <Corridor scenario={scenario} price={price} scale={scale} size="hero" animate />
      <div className="relative h-10 type-small type-number text-ink-secondary" aria-hidden="true">
        <PositionedLabel at={scale.position(scenario.seller_minimum)}>
          Seller&rsquo;s floor
          <br />
          <span className="text-ink">{formatPrice(scenario.seller_minimum)}</span>
        </PositionedLabel>
        <PositionedLabel at={scale.position(scenario.buyer_maximum)}>
          Buyer&rsquo;s ceiling
          <br />
          <span className="text-ink">{formatPrice(scenario.buyer_maximum)}</span>
        </PositionedLabel>
      </div>
    </figure>
  );
}
