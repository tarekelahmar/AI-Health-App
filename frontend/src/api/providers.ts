import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function whoopConnect(userId: number) {
  const r = await axios.get(`${API_BASE}/api/v1/providers/whoop/connect`, { params: { user_id: userId } });
  return r.data as { provider: string; authorize_url: string };
}

export async function whoopStatus(userId: number) {
  const r = await axios.get(`${API_BASE}/api/v1/providers/whoop/status`, { params: { user_id: userId } });
  return r.data as { provider: string; connected: boolean };
}

export async function whoopSync(userId: number, days = 30) {
  const r = await axios.post(`${API_BASE}/api/v1/providers/whoop/sync`, null, { params: { user_id: userId, days } });
  return r.data as { provider: string; inserted: number; rejected: number; errors: any[] };
}

