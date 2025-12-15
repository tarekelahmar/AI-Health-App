import axios from "axios";
import type { CheckIn, CheckInUpsertRequest } from "../types/CheckIn";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getCheckIn(userId: number, dateISO: string): Promise<CheckIn> {
  const res = await axios.get(`${API_BASE}/api/v1/checkins/${dateISO}`, {
    params: { user_id: userId },
  });
  return res.data;
}

export async function upsertCheckIn(payload: CheckInUpsertRequest): Promise<CheckIn> {
  const res = await axios.post(`${API_BASE}/api/v1/checkins/upsert`, payload);
  return res.data;
}

export async function patchCheckIn(userId: number, dateISO: string, patch: Partial<CheckIn>): Promise<CheckIn> {
  const res = await axios.patch(`${API_BASE}/api/v1/checkins/${dateISO}`, patch, {
    params: { user_id: userId },
  });
  return res.data;
}

