export type CheckIn = {
  id: number;
  user_id: number;
  checkin_date: string;

  // V2 slider fields (1.0-10.0 float)
  overall_wellbeing?: number | null;
  energy?: number | null;
  mood?: number | null;
  focus?: number | null;
  connection?: number | null;

  // V1 deprecated fields
  sleep_quality?: number | null;
  stress?: number | null;

  notes?: string | null;
  behaviors_json: Record<string, any>;
  adherence_rate?: number | null;

  // AI companion fields (Phase 2)
  ai_inferred_json?: Record<string, any> | null;
  context_tags_json?: Record<string, any> | null;
  ai_response_text?: string | null;
  discrepancy_json?: Record<string, any> | null;

  // Entry metadata
  word_count?: number | null;
  depth_level?: number | null;

  created_at: string;
  updated_at: string;
};

export type CheckInUpsertRequest = {
  user_id: number;
  checkin_date: string;

  // V2 slider fields (1.0-10.0 float)
  overall_wellbeing?: number | null;
  energy?: number | null;
  mood?: number | null;
  focus?: number | null;
  connection?: number | null;

  // V1 deprecated
  sleep_quality?: number | null;
  stress?: number | null;

  notes?: string | null;
  behaviors_json?: Record<string, any>;
};

