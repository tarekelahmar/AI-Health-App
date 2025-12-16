export interface MetricPoint {
  timestamp: string;
  value: number;
}

export interface MetricBaseline {
  mean: number | null;
  std: number | null;
  available: boolean;
  reason: string | null;
}

export interface MetricSeriesResponse {
  metric_key: string;
  points: MetricPoint[];
  baseline: MetricBaseline;
}

