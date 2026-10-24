import { CheckCircleIcon, WarningCircleIcon } from "@phosphor-icons/react/dist/ssr";

import type { SummaryRecord } from "@/lib/types";

export function RunStatus({ summary }: { summary: SummaryRecord }) {
  if (summary.status === "finished") {
    return (
      <span className="inline-flex items-center gap-1.5 type-small text-ink-secondary">
        <CheckCircleIcon weight="fill" className="size-4 text-ink" aria-hidden="true" />
        Finished
      </span>
    );
  }
  if (summary.status === "interrupted") {
    return (
      <span className="inline-flex items-center gap-1.5 type-small text-ink-secondary">
        <WarningCircleIcon weight="fill" className="size-4 text-warning" aria-hidden="true" />
        Interrupted at {summary.completed_games} of {summary.total_games} games
      </span>
    );
  }
  return <RunProgress summary={summary} />;
}

function RunProgress({ summary }: { summary: SummaryRecord }) {
  const share = summary.total_games ? summary.completed_games / summary.total_games : 0;
  return (
    <span className="inline-flex items-center gap-3 type-small text-ink-secondary">
      <span className="inline-flex items-center gap-1.5">
        <span className="size-2 rounded-full bg-ink animate-live" aria-hidden="true" />
        Running
      </span>
      <span
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={summary.total_games}
        aria-valuenow={summary.completed_games}
        aria-label="Games played"
        className="relative h-1.5 w-28 overflow-hidden rounded-full bg-sunken"
      >
        <span
          className="absolute inset-y-0 left-0 rounded-full bg-ink transition-[width] duration-500"
          style={{ width: `${(share * 100).toFixed(1)}%` }}
        />
      </span>
      <span className="type-number">
        {summary.completed_games} of {summary.total_games} games
      </span>
    </span>
  );
}
