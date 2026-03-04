import apiClient from './client';

export interface UserPreferences {
  preferred_depth_level: number;
  journal_onboarded: boolean;
}

export async function getPreferences(): Promise<UserPreferences> {
  const res = await apiClient.get('/preferences');
  return res.data;
}

export async function updatePreferences(
  data: Partial<UserPreferences>,
): Promise<UserPreferences> {
  const res = await apiClient.patch('/preferences', data);
  return res.data;
}
