const priceFormat = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const MINUS = "−";
const EMPTY = "–";

export function formatPrice(price: number | null): string {
  return price === null ? EMPTY : priceFormat.format(price);
}

export function formatScore(score: number | null): string {
  if (score === null) return EMPTY;
  const percent = score * 100;
  const rounded = Math.abs(percent) < 0.05 ? 0 : percent;
  const sign = rounded > 0 ? "+" : rounded < 0 ? MINUS : "";
  return `${sign}${Math.abs(rounded).toFixed(1)}%`;
}

export function formatShare(share: number | null): string {
  return share === null ? EMPTY : `${Math.round(share * 100)}%`;
}

export function formatCost(dollars: number): string {
  if (dollars === 0) return "$0";
  if (dollars < 0.01) return `$${dollars.toFixed(4)}`;
  return `$${dollars.toFixed(2)}`;
}

const KNOWN_MODELS: Record<string, string> = {
  "deepseek/deepseek-v4.1-flash": "DeepSeek V4.1 Flash",
  "nvidia/nemotron-3-super-120b-a12b": "Nemotron 3 Super",
  "openai/gpt-oss-120b": "gpt-oss-120b",
};

export function modelLabel(modelId: string): string {
  const known = KNOWN_MODELS[modelId];
  if (known) return known;
  const name = modelId.split("/").pop() ?? modelId;
  return name.replace(/[-_]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function modelVendor(modelId: string): string {
  return modelId.includes("/") ? modelId.split("/")[0] : "";
}

export function scenarioLabel(name: string): string {
  const words = name.replace(/[-_]+/g, " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

const RUN_ID = /^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})$/;

export function runDate(runId: string): Date | null {
  const match = RUN_ID.exec(runId);
  if (!match) return null;
  const [, year, month, day, hour, minute, second] = match.map(Number);
  return new Date(year, month - 1, day, hour, minute, second);
}

export function formatRunName(runId: string): string {
  const date = runDate(runId);
  if (!date) return runId;
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function plural(count: number, singular: string, pluralForm = `${singular}s`): string {
  return `${count.toLocaleString("en-US")} ${count === 1 ? singular : pluralForm}`;
}
