import type { DriversResponse } from "../types/Drivers";
import apiClient from "./client";

export async function fetchRecentDrivers(userId: number, limit = 50): Promise<DriversResponse> {
  const res = await apiClient.get("/drivers/recent", {
    // user_id is derived from auth (token or public-mode interceptor)
    params: { limit },
  });
  return res.data;
}

export async function fetchDriversByMetric(userId: number, metricKey: string, limit = 50): Promise<DriversResponse> {
  const res = await apiClient.get("/drivers/by-metric", {
    params: { metric_key: metricKey, limit },
  });
  return res.data;
}

export async function generateDrivers(userId: number, windowDays = 28): Promise<DriversResponse> {
  const res = await apiClient.post(
    "/drivers/generate",
    {
      window_days: windowDays,
      max_findings: 50,
    },
    {},
  );
  return res.data;
}

