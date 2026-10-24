import Link from "next/link";

import { MotifMark } from "@/components/Wordmark";

export default function NotFound() {
  return (
    <section className="flex max-w-2xl flex-col gap-6 py-16">
      <MotifMark className="h-16 w-28" />
      <h1 className="type-title">Nothing here</h1>
      <p className="type-body text-ink-secondary">
        That run or game isn&rsquo;t in the runs folder. It may have been moved or deleted.
      </p>
      <Link href="/" className="focus-ring press w-fit rounded-md bg-ink px-4 py-2 type-small text-page">
        Show the latest run
      </Link>
    </section>
  );
}
