import type { HeadToHead } from "@/lib/games";
import { formatScore, modelLabel } from "@/lib/format";

import { RoleMark } from "./RoleMark";

function clampShare(share: number): number {
  return Math.min(1, Math.max(0, share));
}

function SplitTrack({ cell }: { cell: HeadToHead }) {
  const share = cell.meanSellerShare;
  return (
    <div className="relative h-3" aria-hidden="true">
      <div className="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-zone" />
      <div className="absolute top-0 left-0 h-3 w-0.5 rounded-full bg-buyer" />
      <div className="absolute top-0 right-0 h-3 w-0.5 rounded-full bg-seller" />
      <div className="absolute top-0 left-1/2 h-3 w-px bg-line" />
      {share !== null && (
        <div
          className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-ink ring-2 ring-surface"
          style={{ left: `${clampShare(share) * 100}%` }}
        />
      )}
    </div>
  );
}

function cellDescription(cell: HeadToHead): string {
  return `${cell.deals} of ${cell.games} games ended in a deal. Mean buyer score ${formatScore(cell.meanBuyerScore)}, mean seller score ${formatScore(cell.meanSellerScore)}.`;
}

function CellScore({ role, score }: { role: "buyer" | "seller"; score: number | null }) {
  return (
    <span className="inline-flex items-center gap-1.5 type-number">
      <RoleMark role={role} />
      {formatScore(score)}
    </span>
  );
}

function Cell({ cell }: { cell: HeadToHead | undefined }) {
  if (!cell) {
    return <td className="rounded-md bg-sunken" aria-label="A model never plays itself" />;
  }
  return (
    <td className="rounded-md bg-surface p-4 align-top shadow-raised">
      <span className="sr-only">{cellDescription(cell)}</span>
      <div className="flex flex-col gap-3" aria-hidden="true">
        <SplitTrack cell={cell} />
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 type-small">
          <span className="flex gap-4">
            <CellScore role="buyer" score={cell.meanBuyerScore} />
            <CellScore role="seller" score={cell.meanSellerScore} />
          </span>
          <span className="type-number text-ink-muted">
            {cell.deals} of {cell.games} deals
          </span>
        </div>
      </div>
    </td>
  );
}

export function HeadToHeadGrid({ models, cells }: { models: string[]; cells: HeadToHead[] }) {
  const lookup = new Map(cells.map((cell) => [`${cell.buyer}|${cell.seller}`, cell]));
  return (
    <section aria-labelledby="head-to-head-heading" className="flex min-w-0 flex-col gap-4">
      <h2 id="head-to-head-heading" className="type-heading">
        Head to head
      </h2>
      <div className="relative overflow-x-auto">
        <table className="w-full min-w-xl border-separate border-spacing-2 -mx-2">
          <thead>
            <tr>
              <th className="w-44 text-left type-small font-normal text-ink-muted">
                <span className="inline-flex items-center gap-1.5">
                  <RoleMark role="buyer" /> Buyer
                  <span className="text-ink-muted">vs</span>
                  <RoleMark role="seller" /> Seller
                </span>
              </th>
              {models.map((seller) => (
                <th key={seller} scope="col" className="text-left type-small font-normal">
                  <span className="inline-flex items-center gap-1.5">
                    <RoleMark role="seller" />
                    {modelLabel(seller)}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {models.map((buyer) => (
              <tr key={buyer}>
                <th scope="row" className="text-left type-small font-normal">
                  <span className="inline-flex items-center gap-1.5">
                    <RoleMark role="buyer" />
                    {modelLabel(buyer)}
                  </span>
                </th>
                {models.map((seller) => (
                  <Cell key={seller} cell={lookup.get(`${buyer}|${seller}`)} />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
