import { MotifMark } from "./Wordmark";

export function EmptyState({ runsDirectory }: { runsDirectory: string }) {
  return (
    <section className="flex max-w-2xl flex-col gap-6 py-16">
      <MotifMark className="h-16 w-28" />
      <h1 className="type-title">No runs yet</h1>
      <p className="type-body text-ink-secondary">
        Start a tournament from the project folder. Games show up here as they finish, and the page
        keeps itself up to date.
      </p>
      <pre className="w-fit rounded-md bg-sunken px-4 py-3 type-code text-ink">uv run negotiate run</pre>
      <p className="type-small text-ink-muted">
        Looking for runs in <code className="type-code">{runsDirectory}</code>. Set RUNS_DIR to read
        from somewhere else.
      </p>
    </section>
  );
}
