/**
 * Actions API — endpoints for action detail screens.
 */
import apiClient from './client';

// -- Types ----------------------------------------------------------------

export interface ActionMention {
  date: string;
  excerpt: string;
  message_id: number;
}

// -- Endpoints ------------------------------------------------------------

/**
 * Get journal messages that mention an action's topic.
 * GET /api/v1/actions/{actionId}/mentions?title=...
 *
 * The title is used to extract keywords for searching journal messages.
 */
export async function getActionMentions(actionId: number, title: string): Promise<ActionMention[]> {
  const res = await apiClient.get<ActionMention[]>(`/actions/${actionId}/mentions`, {
    params: { title },
  });
  return res.data;
}
