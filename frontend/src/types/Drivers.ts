export type ExposureType = "behavior" | "intervention";
export type Direction = "improves" | "worsens" | "unclear";

export interface DriverFinding {
  id: number;
  user_id: number;
  exposure_type: ExposureType;
  exposure_key: string;
  metric_key: string;
  lag_days: number;
  direction: Direction;
  effect_size: number;
  confidence: number;
  coverage: number;
  n_exposure_days: number;
  n_total_days: number;
  window_start: string; // YYYY-MM-DD
  window_end: string;   // YYYY-MM-DD
  details: Record<string, any> | null;
  created_at: string; // ISO
}

export interface DriversResponse {
  count: number;
  items: DriverFinding[];
}

