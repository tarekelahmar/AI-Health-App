import apiClient from './client';
import type { ForecastResponse, ForecastSummary } from '../types/Forecast';

export async function fetchForecast(
  metricKey: string,
  horizon: number = 7
): Promise<ForecastResponse> {
  const res = await apiClient.get(`/forecasts/${metricKey}`, {
    params: { horizon },
  });
  return res.data;
}

export async function fetchAllForecasts(): Promise<{ forecasts: ForecastSummary[] }> {
  const res = await apiClient.get('/forecasts');
  return res.data;
}
