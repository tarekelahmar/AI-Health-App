import axios from "axios";
import type { SafetyDecision, SafetyEvaluateRequest } from "../types/Safety";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function evaluateSafety(req: SafetyEvaluateRequest): Promise<SafetyDecision> {
  const res = await axios.post<SafetyDecision>(`${API_BASE}/api/v1/safety/evaluate`, req);
  return res.data;
}

