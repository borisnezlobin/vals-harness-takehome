function Block({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-sunken motion-reduce:animate-none ${className}`} />;
}

export function RunSkeleton() {
  return (
    <div className="flex flex-col gap-16" aria-busy="true" aria-label="Loading run">
      <div className="flex flex-col gap-4">
        <Block className="h-10 w-2/3" />
        <Block className="h-5 w-48" />
      </div>
      <Block className="h-80 w-full rounded-lg" />
      <Block className="h-64 w-full rounded-lg" />
    </div>
  );
}

export function GameSkeleton() {
  return (
    <div className="flex flex-col gap-10" aria-busy="true" aria-label="Loading game">
      <Block className="h-5 w-56" />
      <Block className="h-10 w-1/2" />
      <Block className="h-64 w-full rounded-xl" />
      <Block className="h-96 w-full rounded-lg" />
    </div>
  );
}
