export type InsightStatus =
  | "detected"
  | "evaluated"
  | "suggested";

export interface InsightEvidence {
  baseline_mean?: number | null;
  recent_mean?: number | null;
  followup_mean?: number | null;
  baseline_std?: number | null;
  recent_std?: number | null;
  delta?: number | null;
  effect_size?: number | null;
  severity_std?: number | null;
  days_consistent?: number | null;
  z_score?: number | null;
  slope_per_day?: number | null;
  instability_ratio?: number | null;
  window_days?: number | null;
  n_points?: number | null;
  sample_size?: number | null;
  coverage?: number | null;
  claim_level?: number | null;
  triggers_count?: number | null;
  policy_sanitized?: number | null;
  // Allow additional fields from backend without breaking type safety
  [key: string]: number | string | null | undefined | Record<string, unknown>;
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
  // Human-readable explanation fields (deterministic or LLM-generated)
  explanation?: string | null;
  uncertainty?: string | null;
  suggested_next_step?: string | null;
}
