import apiClient from './client';
import type { CheckIn, CheckInUpsertRequest } from '../types/CheckIn';

export async function getCheckIn(userId: number, dateISO: string): Promise<CheckIn> {
  const res = await apiClient.get(`/checkins/${dateISO}`);
  return res.data;
}

export async function upsertCheckIn(payload: CheckInUpsertRequest): Promise<CheckIn> {
  const res = await apiClient.post('/checkins/upsert', payload);
  return res.data;
}

export async function patchCheckIn(userId: number, dateISO: string, patch: Partial<CheckIn>): Promise<CheckIn> {
  const res = await apiClient.patch(`/checkins/${dateISO}`, patch);
  return res.data;
}
