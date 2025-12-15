export type CheckIn = {
  id: number;
  user_id: number;
  checkin_date: string;

  sleep_quality?: number | null;
  energy?: number | null;
  mood?: number | null;
  stress?: number | null;

  notes?: string | null;
  behaviors_json: Record<string, any>;
  adherence_rate?: number | null;

  created_at: string;
  updated_at: string;
};

export type CheckInUpsertRequest = {
  user_id: number;
  checkin_date: string;

  sleep_quality?: number | null;
  energy?: number | null;
  mood?: number | null;
  stress?: number | null;

  notes?: string | null;
  behaviors_json?: Record<string, any>;
};

