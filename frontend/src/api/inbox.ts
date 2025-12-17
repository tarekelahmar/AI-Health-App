/**
 * ALPHA WIRING: Use unified API client
 */
import apiClient from "./client";
import type { InboxListResponse, InboxItem } from "../types/Inbox";

export async function fetchInbox(userId: number, opts?: { limit?: number; unreadOnly?: boolean }) {
  const res = await apiClient.get<InboxListResponse>("/inbox", {
    params: { user_id: userId, limit: opts?.limit ?? 50, unread_only: opts?.unreadOnly ?? false },
  });
  return res.data;
}

export async function markInboxRead(userId: number, itemId: number) {
  const res = await apiClient.post<InboxItem>("/inbox/mark-read", {
    user_id: userId,
    item_id: itemId,
  });
  return res.data;
}

export async function markAllInboxRead(userId: number) {
  const res = await apiClient.post("/inbox/mark-all-read", { user_id: userId });
  return res.data as { ok: boolean; updated: number };
}

