import apiClient from './client';
import { RiskAssessResponse } from '../types/Risk';

export async function fetchRiskAssessment(): Promise<RiskAssessResponse> {
  const res = await apiClient.get('/risk/assess');
  return res.data;
}
