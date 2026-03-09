/**
 * Journal V3 Chat types.
 */

export interface SessionSummary {
  id: number;
  started_at: string;
  daily_score: number | null;
  message_count: number;
  preview: string;
  summary: string | null;
  messages?: SessionMessage[];
}

export interface SessionMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

/** A message as displayed in the UI (may include streaming state) */
export interface ChatMessageData {
  id: number | null; // null while streaming
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  isStreaming?: boolean;
}

/** Grouped messages under a session divider */
export interface SessionGroup {
  session_id: number;
  started_at: string;
  daily_score: number | null;
  score_confirmed: boolean;
  messages: ChatMessageData[];
}

export interface ScoreConfirmResult {
  confirmed: boolean;
  score: number;
  date: string;
}

/** SSE event types from the chat endpoint */
export type SSETokenEvent = {
  type: 'token';
  content: string;
};

export type SSEDoneEvent = {
  type: 'done';
  session_id: number;
  message_id: number;
  proposed_score?: number;
  domain_checkin_due?: boolean;
  extracted_factors?: Record<string, any>;
};

export type SSEEvent = SSETokenEvent | SSEDoneEvent;
