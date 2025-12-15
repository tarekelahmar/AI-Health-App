import axios from "axios";
import type { InsightSummary } from "../types/Summary";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function runDailySummary(userId: number): Promise<InsightSummary> {
  const res = await axios.post<InsightSummary>(
    `${API_BASE}/api/v1/summaries/daily`,
    null,
    { params: { user_id: userId } }
  );
  return res.data;
}

export async function getLatestSummary(
  userId: number,
  period: string = "daily"
): Promise<InsightSummary | null> {
  const res = await axios.get<InsightSummary | null>(
    `${API_BASE}/api/v1/summaries/latest`,
    { params: { user_id: userId, period } }
  );
  return res.data;
}

