export type InsightStatus =
  | "detected"
  | "evaluated"
  | "suggested";

export interface InsightEvidence {
  baseline_mean?: number;
  followup_mean?: number;
  delta?: number;
  effect_size?: number;
  severity_std?: number;
  days_consistent?: number;
}

export interface Insight {
  id: number;
  created_at: string; // ISO datetime
  title: string;
  summary: string;
  metric_key: string;
  // Pure metadata: semantic domain key (may be missing/null for legacy rows).
  domain_key?: string | null;
  confidence: number; // 0..1
  status: InsightStatus;
  evidence: InsightEvidence;
}

