import Link from "next/link";

export function MotifMark({ className = "h-5 w-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 20" aria-hidden="true" className={className}>
      <rect x="9" y="4" width="14" height="12" rx="2" className="fill-zone" />
      <rect x="7.5" y="2" width="3" height="16" rx="1.5" className="fill-seller" />
      <rect x="21.5" y="2" width="3" height="16" rx="1.5" className="fill-buyer" />
      <line x1="0" y1="10" x2="32" y2="10" strokeWidth="1.5" className="stroke-line" />
      <circle cx="17" cy="10" r="3.5" strokeWidth="2" className="fill-ink stroke-page" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <Link href="/" className="focus-ring inline-flex items-center gap-2.5 rounded-sm">
      <MotifMark />
      <span className="type-wordmark">Haggle</span>
    </Link>
  );
}
