import { Suspense } from "react";

import { EmptyState } from "@/components/EmptyState";
import { RunView } from "@/components/RunView";
import { RunSkeleton } from "@/components/Skeletons";
import { getGames, listRuns, runsDirectory } from "@/lib/runs";

async function LatestRun() {
  const [latest] = await listRuns();
  if (!latest) return <EmptyState runsDirectory={runsDirectory()} />;
  const games = await getGames(latest.config.run_id);
  return <RunView run={latest} games={games} />;
}

export default function HomePage() {
  return (
    <Suspense fallback={<RunSkeleton />}>
      <LatestRun />
    </Suspense>
  );
}
