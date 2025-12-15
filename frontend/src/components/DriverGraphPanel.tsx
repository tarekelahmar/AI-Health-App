import { useEffect, useState } from "react";
import { computeDrivers, fetchDrivers } from "../api/graphs";
import { GraphDriverEdge } from "../types/Graph";

type Props = {
  userId: number;
  targetMetric: string;
};

function fmtKind(kind: string) {
  if (kind === "intervention") return "Intervention";
  if (kind === "behavior") return "Behavior";
  return "Metric";
}

export function DriverGraphPanel({ userId, targetMetric }: Props) {
  const [items, setItems] = useState<GraphDriverEdge[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDrivers(userId, targetMetric, 10);
      // If none exist, compute automatically
      if (!data.items || data.items.length === 0) {
        const computed = await computeDrivers(userId, targetMetric, 10);
        setItems(computed.items || []);
      } else {
        setItems(data.items || []);
      }
    } catch (e: any) {
      setError(e?.message || "Failed to load drivers");
    } finally {
      setLoading(false);
    }
  }

  async function recompute() {
    setLoading(true);
    setError(null);
    try {
      const computed = await computeDrivers(userId, targetMetric, 10);
      setItems(computed.items || []);
    } catch (e: any) {
      setError(e?.message || "Failed to compute drivers");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, targetMetric]);

  return (
    <div className="mb-4 rounded border bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-lg font-semibold">Your Top Drivers</div>
          <div className="text-sm text-gray-600">
            Target: <b>{targetMetric}</b> (ranked using lagged effects + interactions)
          </div>
        </div>

        <button
          onClick={recompute}
          className="rounded bg-gray-900 px-3 py-2 text-sm text-white hover:bg-gray-800"
          disabled={loading}
        >
          {loading ? "Computing..." : "Recompute"}
        </button>
      </div>

      {error && <div className="mt-3 text-sm text-red-600">{error}</div>}
      {loading && <div className="mt-3 text-sm text-gray-600">Loading...</div>}

      {!loading && items.length === 0 && (
        <div className="mt-3 text-sm text-gray-600">
          No drivers yet. Start an experiment and log adherence, then recompute.
        </div>
      )}

      <div className="mt-4 space-y-3">
        {items
          .filter((x) => x.score > 0)
          .slice(0, 7)
          .map((edge, idx) => {
            const notes: string[] = edge.details?.interaction_notes || [];
            return (
              <div key={idx} className="rounded border p-3">
                <div className="flex items-center justify-between">
                  <div className="font-semibold">
                    {idx + 1}. {fmtKind(edge.driver_kind)}:{" "}
                    <span className="font-mono">{edge.driver_key}</span>
                  </div>
                  <div className="text-sm text-gray-700">
                    Score: <b>{edge.score.toFixed(3)}</b>
                  </div>
                </div>

                <div className="mt-1 text-sm text-gray-700">
                  Effect: <b>{edge.effect_size.toFixed(2)}</b> ({edge.direction}) • Lag:{" "}
                  <b>{edge.lag_days}</b> day(s) • Confidence:{" "}
                  <b>{Math.round(edge.confidence * 100)}%</b> • Coverage:{" "}
                  <b>{Math.round(edge.coverage * 100)}%</b>
                </div>

                {notes.length > 0 && (
                  <div className="mt-2 rounded border border-yellow-300 bg-yellow-50 p-2 text-sm">
                    <div className="font-semibold">Interaction notes</div>
                    <ul className="mt-1 list-disc pl-5">
                      {notes.slice(0, 3).map((n, i) => (
                        <li key={i}>{n}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            );
          })}
      </div>

      <div className="mt-3 text-xs text-gray-500">
        This is a statistical "driver map", not a diagnosis. Results can be confounded by lifestyle changes and missing data.
      </div>
    </div>
  );
}

