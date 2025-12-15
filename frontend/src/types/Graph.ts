export type DriverKind = "metric" | "intervention" | "behavior";

export type GraphDriverEdge = {
  driver_key: string;
  driver_kind: DriverKind;
  target_metric_key: string;
  lag_days: number;
  direction: "up" | "down";
  effect_size: number;
  confidence: number;
  coverage: number;
  confounder_penalty: number;
  interaction_boost: number;
  score: number;
  details: Record<string, any>;
};

export type DriversResponse = {
  user_id: number;
  target_metric_key: string;
  items: GraphDriverEdge[];
};

