import { useEffect, useState } from "react";
import { Insight } from "../types/Insight";
import { MetricSeriesResponse } from "../types/MetricSeries";
import { fetchInsightsFeed, runInsightsLoop } from "../api/insights";
import { fetchMetricSeries } from "../api/metrics";
import { InsightFeed } from "../components/InsightFeed";
import { MetricChart } from "../components/MetricChart";

const METRIC_OPTIONS: { key: string; label: string }[] = [
  { key: "sleep_duration", label: "Sleep Duration" },
  { key: "sleep_efficiency", label: "Sleep Efficiency" },
  { key: "resting_hr", label: "Resting HR" },
  { key: "hrv_rmssd", label: "HRV (RMSSD)" },
  { key: "steps", label: "Steps" },
  { key: "sleep_quality", label: "Sleep Quality (1–5)" },
  { key: "energy", label: "Energy (1–5)" },
  { key: "stress", label: "Stress (1–5)" },
];

export default function Dashboard() {
  const USER_ID = 1;

  const [insights, setInsights] = useState<Insight[]>([]);
  const [series, setSeries] = useState<MetricSeriesResponse | null>(null);
  const [metricKey, setMetricKey] = useState<string>("sleep_duration");
  const [loading, setLoading] = useState(false);

  async function loadAll(selectedMetric: string) {
    const feed = await fetchInsightsFeed(USER_ID);
    const metricSeries = await fetchMetricSeries(USER_ID, selectedMetric);
    setInsights(feed.items);
    setSeries(metricSeries);
  }

  async function handleRunInsights() {
    setLoading(true);
    await runInsightsLoop(USER_ID);
    await loadAll(metricKey);
    setLoading(false);
  }

  useEffect(() => {
    loadAll(metricKey);
  }, [metricKey]);

  const metricLabel = METRIC_OPTIONS.find((m) => m.key === metricKey)?.label ?? metricKey;

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-xl font-bold">Health Dashboard</h1>
        <button
          onClick={handleRunInsights}
          disabled={loading}
          className="px-4 py-2 rounded bg-black text-white text-sm disabled:opacity-50"
        >
          {loading ? "Running..." : "Run Insights"}
        </button>
      </div>

      <div className="text-xs text-gray-500 mb-2">
        Insights are informational only and not medical diagnoses.
      </div>

      <div className="bg-white border rounded-lg p-4 shadow-sm">
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium">Metric</label>
          <select
            value={metricKey}
            onChange={(e) => setMetricKey(e.target.value)}
            className="border rounded px-2 py-1 text-sm"
          >
            {METRIC_OPTIONS.map((m) => (
              <option key={m.key} value={m.key}>
                {m.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {series && <MetricChart series={series} title={metricLabel} />}

      <div className="bg-white border rounded-lg p-4 shadow-sm">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Insights</h2>
          <div className="text-xs text-gray-500">
            {insights.length} total • {insights.filter(i => i.metric_key === metricKey).length} for {metricLabel}
          </div>
        </div>
        <InsightFeed insights={insights} filterByMetric={metricKey} />
      </div>
    </div>
  );
}
