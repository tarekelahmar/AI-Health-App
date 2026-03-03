export interface FactorMeta {
  type: string;
  label: string;
  category: string;
  icon: string;
}

export interface ExtractedFactor {
  key: string;
  value: any;
  label: string;
  category: string;
  icon: string;
  source: string;
}

export interface FactorExtractionResponse {
  factors: ExtractedFactor[];
  custom_factors: ExtractedFactor[];
  extraction_method: string; // "llm" | "manual_only"
}

export interface JournalPatternData {
  pattern_name: string;
  pattern_type: string;
  input_factors: string[];
  output_metric: string;
  mean_with: number;
  mean_without: number;
  effect_size: number;
  exceptions: number;
  description: string;
  icon: string;
  data_summary: string;
  confidence: number;
  status: string;
  n_observations: number;
}

export interface PatternComputeResult {
  patterns_found: number;
  patterns_updated: number;
  patterns_new: number;
  minimum_entries_met: boolean;
  entries_count: number;
  entries_needed: number;
}

// Known factors for the manual picker (mirrors backend KNOWN_FACTORS)
export const KNOWN_FACTORS: Record<string, FactorMeta> = {
  exercised: { type: 'bool', label: 'Exercised', category: 'physical', icon: '🏃' },
  social_contact: { type: 'bool', label: 'Social Contact', category: 'social', icon: '👥' },
  isolated: { type: 'bool', label: 'Isolated', category: 'social', icon: '🏠' },
  structured_day: { type: 'bool', label: 'Structured Day', category: 'routine', icon: '📋' },
  worked: { type: 'bool', label: 'Worked', category: 'routine', icon: '💼' },
  alcohol: { type: 'bool', label: 'Alcohol', category: 'substance', icon: '🍷' },
  caffeine_late: { type: 'bool', label: 'Late Caffeine', category: 'substance', icon: '☕' },
  meditation: { type: 'bool', label: 'Meditation', category: 'wellness', icon: '🧘' },
  outdoors: { type: 'bool', label: 'Time Outdoors', category: 'wellness', icon: '🌳' },
  cold_exposure: { type: 'bool', label: 'Cold Exposure', category: 'wellness', icon: '🧊' },
  napped: { type: 'bool', label: 'Napped', category: 'sleep', icon: '😴' },
  late_screen: { type: 'bool', label: 'Late Screen', category: 'sleep', icon: '📱' },
};

export const FACTOR_CATEGORIES = [
  { key: 'physical', label: 'Physical' },
  { key: 'social', label: 'Social' },
  { key: 'routine', label: 'Routine' },
  { key: 'substance', label: 'Substance' },
  { key: 'wellness', label: 'Wellness' },
  { key: 'sleep', label: 'Sleep' },
] as const;
