import apiClient from "./client";
import { MetricSeriesResponse } from "../types/MetricSeries";

export async function fetchMetricSeries(
  userId: number,
  metricKey: string
): Promise<MetricSeriesResponse> {
  const res = await apiClient.get("/metrics/series", {
    params: { user_id: userId, metric_key: metricKey },
  });
  return res.data;
}

