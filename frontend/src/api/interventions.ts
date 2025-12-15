import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function createIntervention(payload: any) {
  const res = await axios.post(`${API_BASE}/api/v1/interventions`, payload);
  return res.data;
}

export async function listInterventions(user_id: number) {
  const res = await axios.get(`${API_BASE}/api/v1/interventions`, { params: { user_id } });
  return res.data;
}

