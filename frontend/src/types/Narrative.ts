export type PeriodType = "daily" | "weekly";

export interface NarrativeResponse {
  id: number;
  user_id: number;
  period_type: PeriodType;
  period_start: string; // YYYY-MM-DD
  period_end: string;   // YYYY-MM-DD
  title: string;
  summary: string;
  key_points: any[];
  drivers: Array<Record<string, any>>;
  actions: Array<Record<string, any>>;
  risks: Array<Record<string, any>>;
  metadata: Record<string, any>;
  created_at: string; // ISO
}

export interface NarrativeListResponse {
  count: number;
  items: NarrativeResponse[];
}

