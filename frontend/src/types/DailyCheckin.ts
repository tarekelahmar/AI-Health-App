/**
 * Minimal type for DailyCheckIn data used by the Actions tab.
 */
export interface DailyCheckinData {
  id: number;
  checkin_date: string;
  overall_wellbeing: number | null;
  behaviors_json: Record<string, any> | null;
}
