import apiClient from './client';
import type { CheckIn, CheckInUpsertRequest } from '../types/CheckIn';
import type { DailyCheckinData } from '../types/DailyCheckin';

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

/**
 * Fetch today's DailyCheckIn (if one exists).
 *
 * Uses the LIST endpoint (not the single-date GET) to avoid
 * auto-creating phantom DailyCheckIn rows on read.
 * Returns null when no check-in exists for today.
 */
export async function getTodayCheckin(): Promise<DailyCheckinData | null> {
  const today = new Date().toISOString().split('T')[0];
  const res = await apiClient.get('/checkins', {
    params: { start_date: today, end_date: today, limit: 1 },
  });
  const items: DailyCheckinData[] = res.data;
  return items.length > 0 ? items[0] : null;
}
