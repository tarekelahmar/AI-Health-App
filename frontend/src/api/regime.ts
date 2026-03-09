import apiClient from './client';
import { RegimeClassification } from '../types/Regime';

export async function fetchCurrentRegime(): Promise<RegimeClassification> {
  const res = await apiClient.get('/regime/current');
  return res.data;
}
