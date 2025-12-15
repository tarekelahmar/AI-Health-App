import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MetricSeriesResponse } from "../types/MetricSeries";
import { fetchMetricSeries } from "../api/metrics";
import { MetricChart } from "../components/MetricChart";

const USER_ID = 1;

const METRIC_OPTIONS: { key: string; label: string }[] = [
  { key: "sleep_duration", label: "Sleep Duration" },
  { key: "sleep_efficiency", label: "Sleep Efficiency" },
  { key: "resting_hr", label: "Resting HR" },
  { key: "hrv_rmssd", label: "HRV (RMSSD)" },
  { key: "steps", label: "Steps" },
  { key: "sleep_quality", label: "Sleep Quality" },
  { key: "energy", label: "Energy" },
  { key: "stress", label: "Stress" },
];

export default function MetricsPage() {
  const navigate = useNavigate();
  const [metricIndex, setMetricIndex] = useState(0);
  const [series, setSeries] = useState<MetricSeriesResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const currentMetric = METRIC_OPTIONS[metricIndex];

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const data = await fetchMetricSeries(USER_ID, currentMetric.key);
        setSeries(data);
      } catch (error) {
        console.error("Failed to load metric", error);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [currentMetric.key]);

  const handlePrev = () => {
    setMetricIndex((prev) => (prev > 0 ? prev - 1 : METRIC_OPTIONS.length - 1));
  };

  const handleNext = () => {
    setMetricIndex((prev) => (prev < METRIC_OPTIONS.length - 1 ? prev + 1 : 0));
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-md mx-auto p-4">
        <div className="flex items-center gap-4 mb-4">
          <button onClick={() => navigate("/dashboard")} className="text-gray-600">
            ← Back
          </button>
          <h1 className="text-xl font-semibold text-gray-900">Metrics</h1>
        </div>

        {/* Metric selector */}
        <div className="bg-white rounded-lg p-4 mb-4">
          <div className="flex items-center justify-between mb-2">
            <button onClick={handlePrev} className="text-gray-600">
              ←
            </button>
            <h2 className="text-lg font-medium">{currentMetric.label}</h2>
            <button onClick={handleNext} className="text-gray-600">
              →
            </button>
          </div>
          <div className="text-xs text-gray-500 text-center">
            {metricIndex + 1} of {METRIC_OPTIONS.length}
          </div>
        </div>

        {/* Chart */}
        {loading ? (
          <div className="bg-white rounded-lg p-8 text-center text-gray-500">Loading...</div>
        ) : series ? (
          <div className="bg-white rounded-lg p-4">
            <MetricChart series={series} />
            <div className="mt-4 text-xs text-gray-500 text-center">
              Scroll to see more metrics
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-lg p-8 text-center text-gray-500">
            No data available
          </div>
        )}
      </div>
    </div>
  );
}

