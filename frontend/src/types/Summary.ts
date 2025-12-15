export interface InsightSummary {
  id: number;
  user_id: number;
  period: string;
  summary_date: string;
  headline: string;
  narrative: string;
  key_metrics: string[];
  drivers: any[];
  interventions: number[];
  outcomes: string[];
  confidence: number;
}

