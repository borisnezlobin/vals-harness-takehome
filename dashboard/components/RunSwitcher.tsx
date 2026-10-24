"use client";

import { CaretUpDownIcon } from "@phosphor-icons/react";
import { useParams, useRouter } from "next/navigation";

export type RunOption = { runId: string; label: string };

export function RunSwitcher({ runs }: { runs: RunOption[] }) {
  const router = useRouter();
  const params = useParams<{ runId?: string }>();
  const current = params.runId ?? runs[0]?.runId ?? "";
  if (runs.length === 0) return null;
  return (
    <label className="relative inline-flex items-center">
      <span className="sr-only">Show run</span>
      <select
        value={current}
        onChange={(event) => router.push(`/runs/${event.target.value}`)}
        className="focus-ring h-9 appearance-none rounded-md bg-sunken pr-9 pl-3 type-small text-ink hover:bg-zone"
      >
        {runs.map((run) => (
          <option key={run.runId} value={run.runId}>
            {run.label}
          </option>
        ))}
      </select>
      <CaretUpDownIcon
        className="pointer-events-none absolute right-3 size-4 text-ink-muted"
        aria-hidden="true"
      />
    </label>
  );
}
