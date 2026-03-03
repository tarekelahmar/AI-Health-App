export type RegimeType =
  | 'normal'
  | 'illness'
  | 'travel'
  | 'high_stress'
  | 'recovery'
  | 'training_peak'
  | 'menstrual_phase';

export interface RegimeClassification {
  regime: RegimeType;
  confidence: number;
  contributing_signals: string[];
  context: string;
  date: string;
}
