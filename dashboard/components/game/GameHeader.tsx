import { ArrowLeftIcon } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";

import { formatCost, formatPrice, formatScore, modelLabel, scenarioLabel } from "@/lib/format";
import type { GameRecord, RoleName } from "@/lib/types";

import { CorridorHero } from "../Corridor";
import { ROLE_TITLE, RoleMark } from "../RoleMark";

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function Party({ game, role }: { game: GameRecord; role: RoleName }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="inline-flex items-center gap-1.5 type-small text-ink-secondary">
        <RoleMark role={role} />
        {ROLE_TITLE[role]}
      </span>
      <span className="type-name">{modelLabel(game.models[role])}</span>
      <span className="type-figure-sm">
        <span className="sr-only">Score </span>
        {formatScore(game.scores[role])}
      </span>
    </div>
  );
}

function endingText(game: GameRecord): string {
  if (game.outcome.ended_by_agreement) return "Both sides asked to end";
  return "Ran out of turns";
}

function Facts({ game }: { game: GameRecord }) {
  const facts = [
    { label: "Turns played", value: String(game.outcome.turns_played) },
    { label: "How it ended", value: endingText(game) },
    { label: "Bad tool calls", value: String(game.outcome.rejected_actions) },
    { label: "Cost", value: formatCost(game.usage.cost_usd) },
  ];
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
      {facts.map((fact) => (
        <div key={fact.label} className="flex flex-col">
          <dt className="type-small text-ink-muted">{fact.label}</dt>
          <dd className="type-body type-number">{fact.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function GameHeader({ game, runId }: { game: GameRecord; runId: string }) {
  const price = game.outcome.deal_price;
  return (
    <header className="flex flex-col gap-8">
      <Link
        href={`/runs/${runId}#games-heading`}
        className="focus-ring inline-flex w-fit items-center gap-2 rounded-sm type-small text-ink-secondary hover:text-ink"
      >
        <ArrowLeftIcon className="size-4" aria-hidden="true" />
        Back to every game in this run
      </Link>
      <div className="flex flex-col gap-2">
        <h1 className="type-title">{scenarioLabel(game.scenario.name)}</h1>
        <p className="max-w-prose type-body text-ink-secondary">{capitalize(game.scenario.item)}.</p>
      </div>
      <div className="grid gap-8 rounded-xl bg-surface p-6 shadow-raised md:grid-cols-12 md:p-8">
        <div className="flex flex-col gap-6 md:col-span-7">
          <span className="type-figure">{price === null ? "No deal" : formatPrice(price)}</span>
          <CorridorHero scenario={game.scenario} price={price} />
        </div>
        <div className="flex flex-col gap-6 md:col-span-5">
          <div className="grid grid-cols-2 gap-6">
            <Party game={game} role="buyer" />
            <Party game={game} role="seller" />
          </div>
          <Facts game={game} />
        </div>
      </div>
    </header>
  );
}
