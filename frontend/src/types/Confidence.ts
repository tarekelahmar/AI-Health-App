export type ConfidenceLevel = "low" | "medium" | "high";

export type UncertaintyReason =
  | "insufficient_data"
  | "high_variability"
  | "short_duration"
  | "confounding_signals"
  | "inconsistent_effect";

export interface ConfidenceBreakdown {
  level: ConfidenceLevel;
  score: number; // 0–1
  data_coverage_days: number;
  consistency_ratio: number;
  effect_size?: number;
  uncertainty_reasons: UncertaintyReason[];
}

export interface InsightUncertaintyUX {
  confidence: ConfidenceBreakdown;
  interpretation_guidance: string;
  safe_next_step: string;
}

