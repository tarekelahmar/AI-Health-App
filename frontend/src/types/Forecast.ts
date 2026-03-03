export interface PredictionPoint {
  date: string;
  predicted: number;
  ci_80_low: number;
  ci_80_high: number;
  ci_95_low: number;
  ci_95_high: number;
}

export interface HistoricalPoint {
  date: string;
  value: number;
}

export interface ForecastResponse {
  metric_key: string;
  historical: HistoricalPoint[];
  predictions: PredictionPoint[];
  message?: string;
  metadata?: {
    training_points: number;
    method: string;
    horizon: number;
  };
}

export interface ForecastSummary {
  metric_key: string;
  available: boolean;
  current_value?: number;
  forecast_3d?: number;
  direction?: 'up' | 'down' | 'stable';
}
