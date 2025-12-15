import axios from "axios";
import type { InboxListResponse, InboxItem } from "../types/Inbox";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function fetchInbox(userId: number, opts?: { limit?: number; unreadOnly?: boolean }) {
  const res = await axios.get<InboxListResponse>(`${API_BASE}/api/v1/inbox`, {
    params: { user_id: userId, limit: opts?.limit ?? 50, unread_only: opts?.unreadOnly ?? false },
  });
  return res.data;
}

export async function markInboxRead(userId: number, itemId: number) {
  const res = await axios.post<InboxItem>(`${API_BASE}/api/v1/inbox/mark-read`, {
    user_id: userId,
    item_id: itemId,
  });
  return res.data;
}

export async function markAllInboxRead(userId: number) {
  const res = await axios.post(`${API_BASE}/api/v1/inbox/mark-all-read`, { user_id: userId });
  return res.data as { ok: boolean; updated: number };
}

