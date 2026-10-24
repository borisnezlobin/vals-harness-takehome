import { formatCost, formatScore, modelLabel, modelVendor } from "@/lib/format";
import type { ModelStatsRecord, RoleName } from "@/lib/types";

import { ROLE_TITLE, RoleMark } from "./RoleMark";

type Axis = { extent: number; zero: number; width: (score: number) => number };

function scoreAxis(board: ModelStatsRecord[]): Axis {
  const largest = Math.max(
    0.1,
    ...board.flatMap((stats) => [
      Math.abs(stats.buyer.mean_score ?? 0),
      Math.abs(stats.seller.mean_score ?? 0),
    ]),
  );
  const extent = Math.ceil(largest / 0.05) * 0.05;
  return { extent, zero: 0.5, width: (score) => Math.min(0.5, Math.abs(score) / (2 * extent)) };
}

function ScoreBar({ role, score, axis }: { role: RoleName; score: number | null; axis: Axis }) {
  const fill = role === "buyer" ? "bg-buyer" : "bg-seller";
  const value = score ?? 0;
  const left = value < 0 ? axis.zero - axis.width(value) : axis.zero;
  const radius = value < 0 ? "rounded-l-sm" : "rounded-r-sm";
  return (
    <div className="grid-score-bar">
      <span className="inline-flex items-center gap-1.5 type-small type-number text-ink-secondary">
        <RoleMark role={role} />
        <span className="sr-only">{ROLE_TITLE[role]} score</span>
        {formatScore(score)}
      </span>
      <div className="relative h-2.5">
        <div
          className="absolute -inset-y-1 w-px bg-ink-muted"
          style={{ left: `${axis.zero * 100}%` }}
        />
        {score !== null && (
          <div
            className={`absolute inset-y-0 ${radius} ${fill}`}
            style={{ left: `${left * 100}%`, width: `${axis.width(value) * 100}%` }}
          />
        )}
      </div>
    </div>
  );
}

function AxisLegend({ axis }: { axis: Axis }) {
  return (
    <div className="relative h-5 type-small text-ink-muted" aria-hidden="true">
      <span className="absolute left-0 type-number">{formatScore(-axis.extent)}</span>
      <span className="absolute left-1/2 -translate-x-1/2">At own limit</span>
      <span className="absolute right-0 type-number">{formatScore(axis.extent)}</span>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <dt className="type-small text-ink-muted">{label}</dt>
      <dd className="type-body type-number">{value}</dd>
    </div>
  );
}

function LeaderRow({ stats, rank, axis }: { stats: ModelStatsRecord; rank: number; axis: Axis }) {
  const leader = rank === 1;
  return (
    <li className="grid-leader-row gap-y-4 py-6">
      <span className="type-figure-sm text-ink-muted">{rank}</span>
      <div className="flex flex-col gap-1">
        <span className="type-name">{modelLabel(stats.model)}</span>
        <span className="type-small text-ink-muted">{modelVendor(stats.model)}</span>
      </div>
      <span className={`col-start-2 lg:col-start-auto ${leader ? "type-figure" : "type-figure-sm"}`}>
        <span className="sr-only">Overall score </span>
        {formatScore(stats.mean_score)}
      </span>
      <div className="col-start-2 flex flex-col gap-2 lg:col-start-auto">
        <ScoreBar role="buyer" score={stats.buyer.mean_score} axis={axis} />
        <ScoreBar role="seller" score={stats.seller.mean_score} axis={axis} />
      </div>
      <dl className="col-start-2 flex gap-6 lg:col-start-auto">
        <Fact label="Deals" value={`${stats.deals} of ${stats.games}`} />
        <Fact label="Bad tool calls" value={String(stats.rejected_actions)} />
        <Fact label="Cost" value={formatCost(stats.cost_usd)} />
      </dl>
    </li>
  );
}

export function Leaderboard({ board }: { board: ModelStatsRecord[] }) {
  const axis = scoreAxis(board);
  return (
    <section aria-labelledby="leaderboard-heading" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h2 id="leaderboard-heading" className="type-heading">
          Leaderboard
        </h2>
        <ul className="flex gap-5 type-small text-ink-secondary" aria-label="Legend">
          {(["buyer", "seller"] as const).map((role) => (
            <li key={role} className="inline-flex items-center gap-1.5">
              <RoleMark role={role} />
              Mean score as {role}
            </li>
          ))}
        </ul>
      </div>
      <div className="rounded-lg bg-surface px-6 shadow-raised">
        <div className="grid-leader-row hidden pt-5 lg:grid" aria-hidden="true">
          <span className="col-start-3 type-small text-ink-muted">Overall</span>
          <div className="grid-score-bar">
            <span />
            <AxisLegend axis={axis} />
          </div>
        </div>
        <ol className="divide-y divide-line" aria-label="Models ranked by overall score">
          {board.map((stats, index) => (
            <LeaderRow key={stats.model} stats={stats} rank={index + 1} axis={axis} />
          ))}
        </ol>
      </div>
    </section>
  );
}
