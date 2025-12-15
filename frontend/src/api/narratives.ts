import axios from "axios";
import type { NarrativeResponse, NarrativeListResponse } from "../types/Narrative";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function fetchDailyNarrative(userId: number, dayISO: string): Promise<NarrativeResponse> {
  const res = await axios.get(`${API_BASE}/api/v1/narratives/daily`, {
    params: { user_id: userId, day: dayISO },
  });
  return res.data;
}

export async function fetchRecentNarratives(userId: number, periodType: "daily" | "weekly" = "daily", limit = 14): Promise<NarrativeListResponse> {
  const res = await axios.get(`${API_BASE}/api/v1/narratives`, {
    params: { user_id: userId, period_type: periodType, limit },
  });
  return res.data;
}

