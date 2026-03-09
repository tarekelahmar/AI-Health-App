import type { SafetyDecision, SafetyEvaluateRequest } from "../types/Safety";
import apiClient from "./client";

export async function evaluateSafety(req: SafetyEvaluateRequest): Promise<SafetyDecision> {
  const res = await apiClient.post<SafetyDecision>("/safety/evaluate", req);
  return res.data;
}

