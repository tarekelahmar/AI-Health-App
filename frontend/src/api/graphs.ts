import axios from "axios";
import { DriversResponse } from "../types/Graph";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function fetchDrivers(user_id: number, target_metric: string, limit = 10) {
  const res = await axios.get<DriversResponse>(`${API_BASE}/api/v1/graphs/drivers`, {
    params: { user_id, target_metric, limit },
  });
  return res.data;
}

export async function computeDrivers(user_id: number, target_metric: string, limit = 10) {
  const res = await axios.post<DriversResponse>(`${API_BASE}/api/v1/graphs/compute`, null, {
    params: { user_id, target_metric, limit },
  });
  return res.data;
}

