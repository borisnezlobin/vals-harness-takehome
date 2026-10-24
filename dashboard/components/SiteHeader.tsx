import { formatRunName } from "@/lib/format";
import { listRuns } from "@/lib/runs";

import { RunSwitcher } from "./RunSwitcher";
import { Wordmark } from "./Wordmark";

function HeaderFrame({ children }: { children?: React.ReactNode }) {
  return (
    <header className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-4 pt-6 sm:px-8">
      <Wordmark />
      {children}
    </header>
  );
}

export async function SiteHeader() {
  const runs = await listRuns();
  const options = runs.map((run) => ({
    runId: run.config.run_id,
    label: `${formatRunName(run.config.run_id)}, ${run.summary.completed_games} games`,
  }));
  return (
    <HeaderFrame>
      <RunSwitcher runs={options} />
    </HeaderFrame>
  );
}

SiteHeader.Fallback = function SiteHeaderFallback() {
  return <HeaderFrame />;
};
