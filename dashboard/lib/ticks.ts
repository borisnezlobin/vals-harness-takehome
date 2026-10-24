const STEPS = [1, 2, 2.5, 5, 10];

export function niceStep(span: number, targetCount: number): number {
  if (span <= 0) return 1;
  const raw = span / Math.max(1, targetCount);
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const step = STEPS.find((candidate) => candidate * magnitude >= raw) ?? 10;
  return step * magnitude;
}

export function niceTicks(min: number, max: number, targetCount = 4): number[] {
  const step = niceStep(max - min, targetCount);
  const ticks: number[] = [];
  for (let tick = Math.ceil(min / step) * step; tick <= max + step * 1e-9; tick += step) {
    ticks.push(Math.round(tick * 1e6) / 1e6);
  }
  return ticks;
}
