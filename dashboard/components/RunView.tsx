import { formatCost, formatRunName } from "@/lib/format";
import { headToHead, summarizeGame } from "@/lib/games";
import type { GameRecord, RunOverview } from "@/lib/types";

import { GameList } from "./GameList";
import { HeadToHeadGrid } from "./HeadToHeadGrid";
import { Leaderboard } from "./Leaderboard";
import { LiveRefresh } from "./LiveRefresh";
import { RunStatus } from "./RunStatus";

function RunFacts({ run }: { run: RunOverview }) {
  const { config, summary } = run;
  const facts = [
    { label: "Models", value: String(config.models.length) },
    { label: "Scenarios", value: String(config.scenarios.length) },
    { label: "Repeats", value: String(config.repeats) },
    { label: "Turns each", value: String(config.settings.turns_per_side) },
    { label: "Spent", value: formatCost(summary.cost_usd) },
  ];
  return (
    <dl className="flex flex-wrap gap-x-8 gap-y-3">
      {facts.map((fact) => (
        <div key={fact.label} className="flex flex-col">
          <dt className="type-small text-ink-muted">{fact.label}</dt>
          <dd className="type-body type-number">{fact.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function RunView({ run, games }: { run: RunOverview; games: GameRecord[] }) {
  const { config, summary } = run;
  const summaries = games.map(summarizeGame);
  return (
    <>
      <LiveRefresh active={summary.status === "running"} />
      <header className="flex flex-col gap-6">
        <div className="flex flex-col gap-3">
          <h1 className="type-title">Round robin from {formatRunName(config.run_id)}</h1>
          <RunStatus summary={summary} />
        </div>
        <RunFacts run={run} />
      </header>
      {summary.completed_games === 0 ? (
        <p className="type-body text-ink-secondary">
          The first game is still being played. This page updates on its own as games finish.
        </p>
      ) : (
        <>
          <Leaderboard board={summary.leaderboard} />
          <HeadToHeadGrid models={config.models} cells={headToHead(config.models, summaries)} />
          <GameList
            runId={config.run_id}
            models={config.models}
            scenarios={config.scenarios}
            games={summaries}
          />
        </>
      )}
    </>
  );
}
