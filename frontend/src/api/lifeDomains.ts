import apiClient from './client';
import type { LifeDomainScoreData } from '../types/LifeDomain';

export async function getCurrentDomainScores(): Promise<LifeDomainScoreData> {
  const res = await apiClient.get('/life-domains/current');
  return res.data;
}

export async function getDomainScoreHistory(days: number = 30): Promise<LifeDomainScoreData[]> {
  const res = await apiClient.get('/life-domains/history', { params: { days } });
  return res.data;
}
