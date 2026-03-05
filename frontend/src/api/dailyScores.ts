/**
 * Daily Scores API client.
 *
 * Fetches the user's daily wellness scores (1-10 scale) from DailyCheckIn records.
 * Uses the list endpoint to avoid auto-creating phantom rows.
 */
import apiClient from './client';

export interface DailyScore {
  date: string;      // YYYY-MM-DD
  score: number;     // 1.0-10.0
}

/**
 * Fetch daily scores for the last N days.
 *
 * Calls GET /api/v1/checkins?start_date=X&end_date=Y and filters to rows
 * that have a non-null overall_wellbeing value.
 */
export async function getDailyScores(days: number = 14): Promise<DailyScore[]> {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - (days - 1));

  const fmt = (d: Date) => d.toISOString().split('T')[0];

  const res = await apiClient.get('/checkins', {
    params: { start_date: fmt(start), end_date: fmt(end), limit: days },
  });

  const items: Array<{ checkin_date: string; overall_wellbeing: number | null }> = res.data;

  return items
    .filter((item) => item.overall_wellbeing != null)
    .map((item) => ({
      date: item.checkin_date,
      score: item.overall_wellbeing!,
    }))
    .sort((a, b) => a.date.localeCompare(b.date));
}
