export type ContributingFactor = {
  metric_key: string;
  label: string;
  z_score: number;
  weight: number;
  direction: 'positive' | 'negative';
  category: 'objective' | 'subjective';
};

export type WellnessScore = {
  id: number;
  user_id: number;
  score_date: string;
  score: number;
  objective_score: number | null;
  subjective_score: number | null;
  contributing_factors: ContributingFactor[];
};
