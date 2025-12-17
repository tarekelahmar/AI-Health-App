/**
 * ALPHA WIRING: Use unified API client
 */
import apiClient from "./client";
import type { NarrativeResponse, NarrativeListResponse } from "../types/Narrative";

export async function fetchDailyNarrative(userId: number, dayISO: string): Promise<NarrativeResponse> {
  const res = await apiClient.get("/narratives/daily", {
    params: { user_id: userId, day: dayISO },
  });
  return res.data;
}

export async function fetchRecentNarratives(userId: number, periodType: "daily" | "weekly" = "daily", limit = 14): Promise<NarrativeListResponse> {
  const res = await apiClient.get("/narratives", {
    params: { user_id: userId, period_type: periodType, limit },
  });
  return res.data;
}

