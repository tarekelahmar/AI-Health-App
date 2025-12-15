import React from "react";
import type { InboxItem } from "../types/Inbox";
import { fetchInbox, markAllInboxRead, markInboxRead } from "../api/inbox";

const badge = (cat: string) => {
  const base = "text-xs px-2 py-0.5 rounded-full border";
  switch (cat) {
    case "reminder":
      return `${base} border-blue-300 text-blue-700`;
    case "insight":
      return `${base} border-green-300 text-green-700`;
    case "experiment":
      return `${base} border-purple-300 text-purple-700`;
    case "safety":
      return `${base} border-red-300 text-red-700`;
    default:
      return `${base} border-gray-300 text-gray-700`;
  }
};

export default function InboxPanel({ userId }: { userId: number }) {
  const [items, setItems] = React.useState<InboxItem[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [unreadOnly, setUnreadOnly] = React.useState(true);

  async function load() {
    setLoading(true);
    try {
      const data = await fetchInbox(userId, { unreadOnly, limit: 50 });
      setItems(data.items);
    } finally {
      setLoading(false);
    }
  }

  React.useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unreadOnly]);

  async function onMarkRead(id: number) {
    await markInboxRead(userId, id);
    await load();
  }

  async function onMarkAll() {
    await markAllInboxRead(userId);
    await load();
  }

  return (
    <div className="rounded-xl border p-4 bg-white">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">Inbox</h2>
          <span className="text-sm text-gray-500">{items.length} items</span>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600 flex items-center gap-2">
            <input
              type="checkbox"
              checked={unreadOnly}
              onChange={(e) => setUnreadOnly(e.target.checked)}
            />
            Unread only
          </label>
          <button
            onClick={onMarkAll}
            className="text-sm px-3 py-1 rounded-lg border hover:bg-gray-50"
          >
            Mark all read
          </button>
          <button
            onClick={load}
            className="text-sm px-3 py-1 rounded-lg border hover:bg-gray-50"
          >
            Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div className="mt-4 text-sm text-gray-500">Loading…</div>
      ) : items.length === 0 ? (
        <div className="mt-4 text-sm text-gray-500">No items.</div>
      ) : (
        <div className="mt-4 space-y-3">
          {items.map((it) => (
            <div key={it.id} className={`rounded-lg border p-3 ${it.is_read ? "opacity-70" : ""}`}>
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className={badge(it.category)}>{it.category}</span>
                  <span className="font-medium">{it.title}</span>
                </div>
                <span className="text-xs text-gray-500">{new Date(it.created_at).toLocaleString()}</span>
              </div>
              <div className="mt-2 text-sm text-gray-700 whitespace-pre-wrap">{it.body}</div>
              <div className="mt-3 flex items-center gap-2">
                {!it.is_read && (
                  <button
                    onClick={() => onMarkRead(it.id)}
                    className="text-sm px-3 py-1 rounded-lg border hover:bg-gray-50"
                  >
                    Mark read
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

