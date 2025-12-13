import axios from "axios";
import { InsightsFeedResponse } from "../types/InsightsFeedResponse";
import { RunInsightsResponse } from "../types/RunInsightsResponse";

const API_BASE = "http://localhost:8000/api/v1";

export async function fetchInsightsFeed(
  userId: number,
  limit = 50
): Promise<InsightsFeedResponse> {
  const res = await axios.get(`${API_BASE}/insights/feed`, {
    params: { user_id: userId, limit },
  });
  return res.data;
}

export async function runInsightsLoop(
  userId: number
): Promise<RunInsightsResponse> {
  const res = await axios.post(`${API_BASE}/insights/run`, null, {
    params: { user_id: userId },
  });
  return res.data;
}

