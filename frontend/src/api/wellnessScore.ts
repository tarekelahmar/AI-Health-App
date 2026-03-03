import apiClient from './client';
import type { WellnessScore } from '../types/WellnessScore';

export async function computeScore(date?: string): Promise<WellnessScore> {
  const res = await apiClient.post('/wellness-score/compute', { score_date: date || null });
  return res.data;
}

export async function getScore(date: string): Promise<WellnessScore | null> {
  const res = await apiClient.get(`/wellness-score/${date}`);
  return res.data;
}

export async function getScoreHistory(days: number = 30): Promise<WellnessScore[]> {
  const res = await apiClient.get('/wellness-score/history', { params: { days } });
  return res.data;
}
