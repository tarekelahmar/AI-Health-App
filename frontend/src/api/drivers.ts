import axios from "axios";
import type { DriversResponse } from "../types/Drivers";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function fetchRecentDrivers(userId: number, limit = 50): Promise<DriversResponse> {
  const res = await axios.get(`${API_BASE}/api/v1/drivers/recent`, {
    params: { user_id: userId, limit },
  });
  return res.data;
}

export async function fetchDriversByMetric(userId: number, metricKey: string, limit = 50): Promise<DriversResponse> {
  const res = await axios.get(`${API_BASE}/api/v1/drivers/by-metric`, {
    params: { user_id: userId, metric_key: metricKey, limit },
  });
  return res.data;
}

export async function generateDrivers(userId: number, windowDays = 28): Promise<DriversResponse> {
  const res = await axios.post(
    `${API_BASE}/api/v1/drivers/generate`,
    {
      window_days: windowDays,
      max_findings: 50,
    },
    {
      params: { user_id: userId },
    }
  );
  return res.data;
}

