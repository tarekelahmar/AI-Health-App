import axios from "axios";

const API_BASE = "http://localhost:8000/api/v1";

export type HealthDataPointIn = {
  metric_key: string;
  value: number;
  timestamp: string; // ISO
  source: "wearable" | "lab" | "questionnaire" | "manual";
  unit?: string | null;
};

export type HealthDataBatchIn = {
  user_id: number;
  points: HealthDataPointIn[];
};

export async function uploadHealthDataBatch(payload: HealthDataBatchIn) {
  const res = await axios.post(`${API_BASE}/health-data/batch`, payload);
  return res.data as { inserted: number; rejected: number; rejected_reasons: string[] };
}

