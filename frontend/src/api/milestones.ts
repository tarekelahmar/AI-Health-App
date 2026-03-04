import apiClient from './client';

export interface MilestoneData {
  id: number;
  milestone_type: string;
  detected_date: string;
  description: string;
  category: string;
  metadata_json: Record<string, any> | null;
}

export interface SynthesisData {
  data: Record<string, any>;
}

export async function getMilestones(limit: number = 20): Promise<MilestoneData[]> {
  const res = await apiClient.get('/journal/milestones', { params: { limit } });
  return res.data;
}

export async function getWeeklySynthesis(): Promise<SynthesisData> {
  const res = await apiClient.get('/journal/synthesis/weekly');
  return res.data;
}

export async function getMonthlySynthesis(month?: string): Promise<SynthesisData> {
  const res = await apiClient.get('/journal/synthesis/monthly', { params: { month } });
  return res.data;
}

export interface PhaseData {
  week_start: string;
  week_end: string;
  phase: string;
  confidence: number;
  avg: number | null;
}

export async function getWeeklyPhases(days: number = 30): Promise<PhaseData[]> {
  const res = await apiClient.get('/journal/phases', { params: { days } });
  return res.data;
}

export async function exportJournalData(): Promise<any> {
  const res = await apiClient.get('/checkins/export');
  return res.data;
}

export async function deleteCheckin(date: string): Promise<void> {
  await apiClient.delete(`/checkins/${date}`);
}
