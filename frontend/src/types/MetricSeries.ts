export interface MetricPoint {
  timestamp: string;
  value: number;
}

export interface MetricBaseline {
  mean: number;
  std: number;
}

export interface MetricSeriesResponse {
  metric_key: string;
  points: MetricPoint[];
  baseline: MetricBaseline;
}

