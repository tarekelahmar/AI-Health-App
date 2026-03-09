export type LifeDomainScoreData = {
  score_date: string;
  scores: Record<string, number>;
  total_score: number;
};

export const LIFE_DOMAIN_LABELS: Record<string, string> = {
  career_work: 'Career & Work',
  relationship: 'Relationship',
  physical_health: 'Physical Health',
  mental_emotional: 'Mental & Emotional',
  social_friendships: 'Social & Friends',
  purpose_meaning: 'Purpose & Meaning',
  finance: 'Finance',
  structure_routine: 'Structure & Routine',
  growth_learning: 'Growth & Learning',
  hobbies_play: 'Hobbies & Play',
};

export const LIFE_DOMAIN_KEYS = Object.keys(LIFE_DOMAIN_LABELS);
