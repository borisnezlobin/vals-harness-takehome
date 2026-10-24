"use client";

import { CaretRightIcon } from "@phosphor-icons/react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { priceScale } from "@/lib/corridor";
import { formatPrice, formatScore, modelLabel, plural, scenarioLabel } from "@/lib/format";
import { type GameSummary, type ScenarioGroup, groupByScenario } from "@/lib/games";
import type { ScenarioRecord } from "@/lib/types";

import { Corridor, corridorDescription } from "./Corridor";
import { RoleMark } from "./RoleMark";
import { SegmentedControl } from "./SegmentedControl";

type OutcomeFilter = "all" | "deal" | "none";

const OUTCOME_OPTIONS: { value: OutcomeFilter; label: string }[] = [
  { value: "all", label: "Every outcome" },
  { value: "deal", label: "Deals" },
  { value: "none", label: "No deal" },
];

function matchesFilters(game: GameSummary, model: string, outcome: OutcomeFilter): boolean {
  const modelMatches = model === "all" || game.models.buyer === model || game.models.seller === model;
  if (!modelMatches) return false;
  if (outcome === "deal") return game.dealPrice !== null;
  if (outcome === "none") return game.dealPrice === null;
  return true;
}

function GameRow({ runId, game, group }: { runId: string; game: GameSummary; group: ScenarioGroup }) {
  const scale = useMemo(
    () =>
      priceScale(
        group.scenario,
        group.games.flatMap((entry) => (entry.dealPrice === null ? [] : [entry.dealPrice])),
      ),
    [group],
  );
  return (
    <li>
      <Link
        href={`/runs/${runId}/games/${game.gameId}`}
        className="focus-ring grid-game-row group rounded-md px-3 py-3 hover:bg-sunken"
      >
        <span className="flex min-w-0 flex-col gap-1 sm:contents">
          <span className="inline-flex min-w-0 items-center gap-1.5 type-small">
            <RoleMark role="buyer" />
            <span className="sr-only">Buyer </span>
            <span className="truncate">{modelLabel(game.models.buyer)}</span>
          </span>
          <span className="inline-flex min-w-0 items-center gap-1.5 type-small">
            <RoleMark role="seller" />
            <span className="sr-only">Seller </span>
            <span className="truncate">{modelLabel(game.models.seller)}</span>
          </span>
        </span>
        <span className="order-last col-span-3 mt-2 sm:order-none sm:col-span-1 sm:mt-0">
          <span className="sr-only">{corridorDescription(game.scenario, game.dealPrice)}</span>
          <Corridor scenario={game.scenario} price={game.dealPrice} scale={scale} />
        </span>
        <span className="text-right type-small type-number">
          {game.dealPrice === null ? (
            <span className="text-ink-muted">No deal</span>
          ) : (
            formatPrice(game.dealPrice)
          )}
        </span>
        <span className="hidden text-right type-small type-number text-ink-muted md:block">
          {formatScore(game.scores.buyer)}
        </span>
        <span className="hidden text-right type-small type-number text-ink-muted md:block">
          {formatScore(game.scores.seller)}
        </span>
        <CaretRightIcon
          className="size-4 text-ink-muted transition-[translate] duration-150 group-hover:translate-x-0.5"
          aria-hidden="true"
        />
      </Link>
    </li>
  );
}

function ScenarioHeader({ scenario }: { scenario: ScenarioRecord }) {
  return (
    <div className="flex flex-col gap-1 px-3">
      <h3 className="type-name">{scenarioLabel(scenario.name)}</h3>
      <dl className="flex flex-wrap gap-x-6 gap-y-1 type-small text-ink-secondary">
        <div className="inline-flex items-center gap-1.5">
          <dt className="inline-flex items-center gap-1.5">
            <span className="h-3 w-0.5 rounded-full bg-seller" aria-hidden="true" />
            Seller&rsquo;s floor
          </dt>
          <dd className="type-number text-ink">{formatPrice(scenario.seller_minimum)}</dd>
        </div>
        <div className="inline-flex items-center gap-1.5">
          <dt className="inline-flex items-center gap-1.5">
            <span className="h-3 w-0.5 rounded-full bg-buyer" aria-hidden="true" />
            Buyer&rsquo;s ceiling
          </dt>
          <dd className="type-number text-ink">{formatPrice(scenario.buyer_maximum)}</dd>
        </div>
        {!scenario.reserves_overlap && (
          <div className="text-ink-secondary">The limits don&rsquo;t overlap</div>
        )}
      </dl>
    </div>
  );
}

function ColumnHeadings() {
  return (
    <div className="grid-game-row px-3 type-small text-ink-muted" aria-hidden="true">
      <span className="sm:hidden">Buyer and seller</span>
      <span className="hidden sm:block">Buyer</span>
      <span className="hidden sm:block">Seller</span>
      <span className="hidden sm:block">Where the price landed</span>
      <span className="text-right">Price</span>
      <span className="hidden text-right md:block">Buyer score</span>
      <span className="hidden text-right md:block">Seller score</span>
      <span />
    </div>
  );
}

export function GameList({
  runId,
  models,
  scenarios,
  games,
}: {
  runId: string;
  models: string[];
  scenarios: ScenarioRecord[];
  games: GameSummary[];
}) {
  const [model, setModel] = useState("all");
  const [outcome, setOutcome] = useState<OutcomeFilter>("all");
  const groups = useMemo(() => groupByScenario(scenarios, games), [scenarios, games]);
  const modelOptions = [
    { value: "all", label: "Every model" },
    ...models.map((id) => ({ value: id, label: modelLabel(id) })),
  ];
  const visibleCount = games.filter((game) => matchesFilters(game, model, outcome)).length;

  return (
    <section aria-labelledby="games-heading" className="flex flex-col gap-6">
      <div className="flex flex-col gap-4">
        <h2 id="games-heading" className="type-heading">
          Games
        </h2>
        <div className="flex flex-wrap items-center gap-3">
          <SegmentedControl label="Model" options={modelOptions} value={model} onChange={setModel} />
          <SegmentedControl
            label="Outcome"
            options={OUTCOME_OPTIONS}
            value={outcome}
            onChange={setOutcome}
          />
          <span className="type-small text-ink-muted" aria-live="polite">
            {plural(visibleCount, "game")}
          </span>
        </div>
      </div>
      <div className="flex flex-col gap-8">
        {groups.map((group) => {
          const visible = group.games.filter((game) => matchesFilters(game, model, outcome));
          if (visible.length === 0) return null;
          return (
            <div key={group.scenario.name} className="flex flex-col gap-3 rounded-lg bg-surface p-3 pt-5 shadow-raised">
              <ScenarioHeader scenario={group.scenario} />
              <ColumnHeadings />
              <ul className="flex flex-col">
                {visible.map((game) => (
                  <GameRow key={game.gameId} runId={runId} game={game} group={group} />
                ))}
              </ul>
            </div>
          );
        })}
        {visibleCount === 0 && (
          <p className="type-body text-ink-secondary">
            No games match these filters yet.
          </p>
        )}
      </div>
    </section>
  );
}
