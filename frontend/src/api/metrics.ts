import axios from "axios";
import { MetricSeriesResponse } from "../types/MetricSeries";

const API_BASE = "http://localhost:8000/api/v1";

export async function fetchMetricSeries(
  userId: number,
  metricKey: string
): Promise<MetricSeriesResponse> {
  const res = await axios.get(`${API_BASE}/metrics/series`, {
    params: { user_id: userId, metric_key: metricKey },
  });
  return res.data;
}

