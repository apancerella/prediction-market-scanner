export interface Bet {
  stake: number;
  price: number;
  contracts: number;
  cost: number;
  fees: number;
  total_cost: number;
  payout: number;
  profit: number;
  return_pct: number;
  annualized_pct: number | null;
  max_loss: number;
  breakeven_prob: number;
  days: number | null;
}

export interface Opportunity {
  id: string;
  strategy: "favorite" | "arbitrage";
  ticker: string;
  event_ticker: string;
  series_ticker: string;
  category: string;
  tags: string[];
  title: string;
  outcome: string;
  side: "yes" | "no";
  price: number;
  bid: number | null;
  spread: number | null;
  implied_prob: number;
  risk: string;
  flags: string[];
  settles_at: string | null;
  days_to_settle: number | null;
  in_progress: boolean;
  volume_24h: number;
  open_interest: number;
  rules: string;
  url: string;
  legs?: { ticker: string; outcome: string; price: number }[];
  bet: Bet;
  score: number;
}

export interface Scan {
  generated_at: string;
  source: string;
  markets_scanned: number;
  stake: number;
  fee_model: Record<string, unknown>;
  criteria: Record<string, Record<string, unknown>>;
  opportunities: Opportunity[];
}

export interface Pick {
  id: string;
  strategy: string;
  ticker: string;
  side: string;
  title: string;
  outcome: string;
  category: string;
  url: string;
  first_seen: string;
  last_seen: string;
  first_price: number;
  last_price: number;
  first_bet: Bet;
  settles_at: string | null;
  samples: [string, number][];
  result: null | { won: boolean; profit: number; staked: number; settled_seen: string };
}

export interface Ledger {
  updated_at: string;
  picks: Record<string, Pick>;
  summary: {
    tracked: number;
    resolved: number;
    wins: number;
    win_rate: number | null;
    profit: number;
    staked: number;
    roi_pct: number | null;
    by_strategy: Record<string, { resolved: number; wins: number; profit: number; staked: number }>;
  };
}

export type Verdict = "strong" | "reasonable" | "pass";

export interface Opinion {
  verdict: Verdict;
  claude_prob: number | null;
  reason: string;
  red_flags: string[];
  price_at_review?: number;
}

export interface Opinions {
  generated_at: string;
  summary: string;
  picks: Record<string, Opinion>;
}
