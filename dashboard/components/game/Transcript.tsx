"use client";

import {
  BrainIcon,
  CaretDownIcon,
  FlagIcon,
  HandshakeIcon,
  type Icon,
  PlugsIcon,
  ScissorsIcon,
  TagIcon,
  WarningIcon,
} from "@phosphor-icons/react";
import type { ReactNode } from "react";

import { splitEmphasis } from "@/lib/emphasis";
import { formatPrice, modelLabel } from "@/lib/format";
import { summarizeTurn } from "@/lib/offers";
import type { RoleName, TurnRecord } from "@/lib/types";

import { ROLE_TITLE, RoleMark } from "../RoleMark";

const ROLE_SURFACE: Record<RoleName, string> = {
  buyer: "bg-buyer-wash md:mr-12",
  seller: "bg-seller-wash md:ml-12",
};

function Chip({ icon: IconComponent, tone = "neutral", children }: { icon: Icon; tone?: "neutral" | "warning"; children: ReactNode }) {
  const iconColor = tone === "warning" ? "text-warning" : "text-ink-secondary";
  return (
    <span className="inline-flex items-center gap-1.5 rounded-sm bg-surface px-2 py-1 type-small text-ink shadow-raised">
      <IconComponent weight="bold" className={`size-3.5 shrink-0 ${iconColor}`} aria-hidden="true" />
      {children}
    </span>
  );
}

function TurnActions({ turn }: { turn: TurnRecord }) {
  const summary = summarizeTurn(turn);
  const chips: ReactNode[] = [];
  if (summary.offered !== null) {
    chips.push(<Chip key="offer" icon={TagIcon}>Offered {formatPrice(summary.offered)}</Chip>);
  }
  if (summary.accepted !== null) {
    chips.push(<Chip key="accept" icon={HandshakeIcon}>Accepted {formatPrice(summary.accepted)}</Chip>);
  }
  if (summary.askedToEnd) {
    chips.push(<Chip key="end" icon={FlagIcon}>Asked to end</Chip>);
  }
  summary.rejections.forEach((rejection, index) => {
    chips.push(<Chip key={`reject-${index}`} icon={WarningIcon} tone="warning">{rejection}</Chip>);
  });
  if (turn.error) {
    chips.push(<Chip key="error" icon={PlugsIcon} tone="warning">The API call failed: {turn.error}</Chip>);
  }
  if (chips.length === 0) return null;
  return <div className="flex flex-wrap gap-2">{chips}</div>;
}

function Reasoning({ text }: { text: string }) {
  const words = text.split(/\s+/).length;
  return (
    <details className="group">
      <summary className="focus-ring inline-flex cursor-pointer list-none items-center gap-1.5 rounded-sm type-small text-ink-secondary hover:text-ink">
        <BrainIcon className="size-4" aria-hidden="true" />
        Read its private reasoning ({words.toLocaleString("en-US")} words)
        <CaretDownIcon className="size-3.5 transition-[rotate] duration-150 group-open:rotate-180" aria-hidden="true" />
      </summary>
      <p className="mt-2 max-w-prose whitespace-pre-wrap type-small text-ink-secondary">{text}</p>
    </details>
  );
}

function Message({ turn }: { turn: TurnRecord }) {
  if (!turn.text) {
    return <p className="type-small text-ink-muted">Sent no message, only tool calls.</p>;
  }
  return (
    <p className="max-w-prose whitespace-pre-wrap type-body">
      {splitEmphasis(turn.text).map((run, index) =>
        run.strong ? <strong key={index} className="font-semibold">{run.text}</strong> : run.text,
      )}
    </p>
  );
}

function TurnCard({
  turn,
  active,
  onHover,
  onSelect,
}: {
  turn: TurnRecord;
  active: boolean;
  onHover: (turn: number | null) => void;
  onSelect: (turn: number) => void;
}) {
  const ring = active ? "ring-2 ring-ink" : "";
  return (
    <li
      id={`turn-${turn.index}`}
      className={`flex scroll-mt-24 flex-col gap-3 rounded-lg p-4 transition-shadow duration-150 ${ROLE_SURFACE[turn.role]} ${ring}`}
      onPointerMove={(event) => {
        if (event.pointerType === "mouse" && !active) onHover(turn.index);
      }}
      onPointerLeave={() => onHover(null)}
      onFocus={() => onSelect(turn.index)}
    >
      <header className="flex items-baseline justify-between gap-3">
        <span className="inline-flex items-center gap-2">
          <RoleMark role={turn.role} className="size-3" />
          <span className="type-name">{modelLabel(turn.model)}</span>
          <span className="type-small text-ink-secondary">{ROLE_TITLE[turn.role]}</span>
        </span>
        <span className="type-small type-number text-ink-muted">Turn {turn.index}</span>
      </header>
      <Message turn={turn} />
      {turn.truncated && (
        <span className="inline-flex items-center gap-1.5 type-small text-ink-secondary">
          <ScissorsIcon className="size-4" aria-hidden="true" />
          Cut off at {turn.text.length.toLocaleString("en-US")} of {turn.original_length.toLocaleString("en-US")} characters
        </span>
      )}
      <TurnActions turn={turn} />
      {turn.reasoning && <Reasoning text={turn.reasoning} />}
    </li>
  );
}

export function Transcript({
  turns,
  activeTurn,
  onHover,
  onSelect,
}: {
  turns: TurnRecord[];
  activeTurn: number | null;
  onHover: (turn: number | null) => void;
  onSelect: (turn: number) => void;
}) {
  return (
    <ol className="flex flex-col gap-3" aria-label="Transcript">
      {turns.map((turn) => (
        <TurnCard
          key={turn.index}
          turn={turn}
          active={turn.index === activeTurn}
          onHover={onHover}
          onSelect={onSelect}
        />
      ))}
    </ol>
  );
}
