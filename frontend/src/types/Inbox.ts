export type InboxCategory = "reminder" | "insight" | "experiment" | "safety" | "system";

export interface InboxItem {
  id: number;
  user_id: number;
  category: InboxCategory | string;
  title: string;
  body: string;
  metadata?: Record<string, any> | null;
  is_read: boolean;
  created_at: string; // ISO
}

export interface InboxListResponse {
  count: number;
  items: InboxItem[];
}

