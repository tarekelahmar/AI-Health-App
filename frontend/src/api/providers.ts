/**
 * ALPHA WIRING: Use unified API client
 */
import apiClient from "./client";

export async function whoopConnect(userId: number) {
  const r = await apiClient.get("/providers/whoop/connect", { params: { user_id: userId } });
  return r.data as { provider: string; authorize_url: string };
}

export async function whoopStatus(userId: number) {
  const r = await apiClient.get("/providers/whoop/status", { params: { user_id: userId } });
  return r.data as { provider: string; connected: boolean };
}

export async function whoopSync(userId: number, days = 30) {
  const r = await apiClient.post("/providers/whoop/sync", null, { params: { user_id: userId, days } });
  return r.data as { provider: string; inserted: number; rejected: number; errors: any[] };
}

