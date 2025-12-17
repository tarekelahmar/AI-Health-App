/**
 * ALPHA WIRING: Use unified API client
 */
import apiClient from "./client";
import { InsightsFeedResponse } from "../types/InsightsFeedResponse";
import { RunInsightsResponse } from "../types/RunInsightsResponse";

export async function fetchInsightsFeed(
  userId: number,
  limit = 50
): Promise<InsightsFeedResponse> {
  const res = await apiClient.get("/insights/feed", {
    params: { user_id: userId, limit },
  });
  return res.data;
}

export async function runInsightsLoop(
  userId: number
): Promise<RunInsightsResponse> {
  const res = await apiClient.post("/insights/run", null, {
    params: { user_id: userId },
  });
  return res.data;
}

