export type DriverType = "behavior" | "supplement" | "intervention" | "lab_marker";
export type Direction = "positive" | "negative" | "neutral";

export interface PersonalDriver {
  id: number;
  user_id: number;
  driver_type: DriverType;
  driver_key: string;
  outcome_metric: string;
  lag_days: number;
  effect_size: number;
  direction: Direction;
  variance_explained: number;
  confidence: number;
  stability: number;
  sample_size: number;
  created_at: string; // ISO
}

export interface PersonalDriversResponse {
  count: number;
  items: PersonalDriver[];
}

export interface TopDriversResponse {
  outcome_metric: string;
  positive: PersonalDriver[];
  negative: PersonalDriver[];
}

