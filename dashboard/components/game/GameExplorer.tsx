"use client";

import { useState } from "react";

import type { GameRecord } from "@/lib/types";

import { RoleMark } from "../RoleMark";
import { OfferChart } from "./OfferChart";
import { Transcript } from "./Transcript";

function scrollToTurn(turn: number) {
  const element = document.getElementById(`turn-${turn}`);
  if (!element) return;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  element.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "nearest" });
}

function ChartLegend() {
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-2 type-small text-ink-secondary" aria-label="Legend">
      <li className="inline-flex items-center gap-1.5">
        <RoleMark role="buyer" />
        Buyer&rsquo;s standing offer
      </li>
      <li className="inline-flex items-center gap-1.5">
        <RoleMark role="seller" />
        Seller&rsquo;s standing offer
      </li>
      <li className="inline-flex items-center gap-1.5">
        <span className="size-2.5 rounded-full bg-ink" aria-hidden="true" />
        Accepted offer
      </li>
    </ul>
  );
}

export function GameExplorer({ game }: { game: GameRecord }) {
  const [hovered, setHovered] = useState<number | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const activeTurn = hovered ?? selected;

  function selectFromChart(turn: number) {
    setHovered(null);
    setSelected(turn);
    scrollToTurn(turn);
  }

  return (
    <div className="grid gap-8 lg:grid-cols-12">
      <section aria-labelledby="offers-heading" className="flex flex-col gap-4 lg:col-span-7 lg:self-start lg:sticky lg:top-6">
        <div className="flex flex-col gap-3">
          <h2 id="offers-heading" className="type-heading">
            Offers by turn
          </h2>
          <ChartLegend />
        </div>
        <div className="rounded-lg bg-surface p-4 shadow-raised">
          <OfferChart
            game={game}
            activeTurn={activeTurn}
            selectedTurn={selected}
            onHover={setHovered}
            onSelect={selectFromChart}
          />
        </div>
      </section>
      <section aria-labelledby="transcript-heading" className="flex flex-col gap-4 lg:col-span-5">
        <h2 id="transcript-heading" className="type-heading">
          Transcript
        </h2>
        <Transcript turns={game.turns} activeTurn={activeTurn} onHover={setHovered} onSelect={setSelected} />
      </section>
    </div>
  );
}
