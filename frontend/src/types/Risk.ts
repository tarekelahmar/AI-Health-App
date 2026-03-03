export type RiskLevel = 'low' | 'moderate' | 'elevated' | 'high';

export interface ContributingFactor {
  metric: string;
  current_value: number;
  baseline_value: number;
  deviation_pct: number;
  direction: 'above' | 'below';
}

export interface RiskAssessment {
  risk_type: string;
  risk_level: RiskLevel;
  risk_score: number;
  description: string;
  recommended_actions: string[];
  contributing_factors: ContributingFactor[];
}

export interface RiskAssessResponse {
  assessments: RiskAssessment[];
  message?: string;
}
