// Mirrors negotiation/records.py. Keep both in sync and bump SCHEMA_VERSION together.
export const SCHEMA_VERSION = 1;

export type RoleName = "buyer" | "seller";
export type ActionName = "propose_offer" | "accept_offer" | "end_negotiation";
export type RunStatus = "running" | "finished" | "interrupted";

export type ActionRecord = {
  kind: ActionName;
  price: number | null;
  accepted: boolean;
  note: string;
};

export type UsageRecord = {
  prompt_tokens: number;
  completion_tokens: number;
  reasoning_tokens: number;
  cost_usd: number;
};

export type TurnRecord = {
  index: number;
  role: RoleName;
  model: string;
  provider: string | null;
  text: string;
  truncated: boolean;
  original_length: number;
  reasoning: string | null;
  actions: ActionRecord[];
  parse_problems: string[];
  raw_tool_calls: { name: string; arguments: string }[];
  standing_offers: Record<RoleName, number | null>;
  deal_after_turn: number | null;
  usage: UsageRecord;
  latency_seconds: number;
  error: string | null;
};

export type ScenarioRecord = {
  name: string;
  item: string;
  seller_minimum: number;
  buyer_maximum: number;
  reference_price: number;
  reserves_overlap: boolean;
};

export type OutcomeRecord = {
  deal_price: number | null;
  deal_accepted_by: RoleName | null;
  ended_by_agreement: boolean;
  turns_played: number;
  api_errors: number;
  rejected_actions: number;
};

export type GameRecord = {
  schema_version: number;
  game_id: string;
  repeat: number;
  scenario: ScenarioRecord;
  models: Record<RoleName, string>;
  outcome: OutcomeRecord;
  scores: Record<RoleName, number>;
  usage: UsageRecord;
  turns: TurnRecord[];
};

export type SettingsRecord = {
  turns_per_side: number;
  message_char_limit: number;
  max_penalty: number;
  max_output_tokens: number;
  temperature: number | null;
  request_attempts: number;
};

export type RunConfigRecord = {
  schema_version: number;
  run_id: string;
  started_at: string;
  models: string[];
  scenarios: ScenarioRecord[];
  repeats: number;
  total_games: number;
  settings: SettingsRecord;
};

export type RoleStatsRecord = {
  games: number;
  deals: number;
  mean_score: number | null;
  mean_surplus_share: number | null;
};

export type ModelStatsRecord = {
  model: string;
  games: number;
  deals: number;
  mean_score: number | null;
  buyer: RoleStatsRecord;
  seller: RoleStatsRecord;
  mean_turns: number | null;
  rejected_actions: number;
  api_errors: number;
  cost_usd: number;
};

export type PairingRecord = {
  buyer_model: string;
  seller_model: string;
  games: number;
  deals: number;
  mean_buyer_score: number | null;
  mean_seller_score: number | null;
};

export type SummaryRecord = {
  schema_version: number;
  run_id: string;
  status: RunStatus;
  updated_at: string;
  finished_at: string | null;
  completed_games: number;
  total_games: number;
  cost_usd: number;
  leaderboard: ModelStatsRecord[];
  pairings: PairingRecord[];
};

export type RunOverview = {
  config: RunConfigRecord;
  summary: SummaryRecord;
};
