import axios from "axios";
import type { PersonalDriversResponse, TopDriversResponse } from "../types/PersonalDrivers";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function fetchPersonalDrivers(userId: number, limit = 100): Promise<PersonalDriversResponse> {
  const res = await axios.get(`${API_BASE}/api/v1/drivers/personal`, {
    params: { user_id: userId, limit },
  });
  return res.data;
}

export async function fetchTopDrivers(userId: number, outcomeMetric: string, limit = 10): Promise<TopDriversResponse> {
  const res = await axios.get(`${API_BASE}/api/v1/drivers/top`, {
    params: { user_id: userId, outcome_metric: outcomeMetric, limit },
  });
  return res.data;
}

export async function recomputePersonalDrivers(userId: number, windowDays = 28): Promise<PersonalDriversResponse> {
  const res = await axios.post(
    `${API_BASE}/api/v1/drivers/recompute`,
    {},
    {
      params: { user_id: userId, window_days: windowDays },
    }
  );
  return res.data;
}

