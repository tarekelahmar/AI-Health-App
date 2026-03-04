export type InferredDimensions = {
  motivation: number | null;
  anxiety_level: number | null;
  self_worth: number | null;
  structure_adherence: number | null;
  emotional_regulation: number | null;
  relationship_quality: number | null;
  sentiment_score: number;
  inferred_overall: number | null;
};

export type ContextTags = {
  exercise: boolean | null;
  exercise_type: string | null;
  social_contact: string | null;
  work_type: string | null;
  sleep: string | null;
  substances: string | null;
  location: string | null;
  conflict: boolean | null;
  conflict_with: string | null;
  achievement: boolean | null;
  achievement_note: string | null;
};

export type CompanionText = {
  text: string;
  pattern_referenced: boolean;
  discrepancy_noted: boolean;
};

export type Discrepancy = {
  rule: string;
  description: string;
  severity: 'info' | 'notable' | 'significant';
};

export type CompanionAnalyzeResponse = {
  extraction_method: 'llm' | 'deterministic_only';
  depth_level: number;
  factors: Record<string, any>;
  custom_factors: Array<{ key: string; value: any; label: string }>;
  ai_inferred: InferredDimensions | null;
  context_tags: ContextTags | null;
  companion_response: CompanionText | null;
  discrepancies: Discrepancy[];
};
