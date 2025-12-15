import React from "react";
import type { InsightSummary } from "../types/Summary";

export function DailyNarrative({ summary }: { summary: InsightSummary }) {
  return (
    <div className="rounded-xl bg-white p-4 shadow">
      <h2 className="text-lg font-semibold">{summary.headline}</h2>
      <p className="mt-2 text-gray-700">{summary.narrative}</p>
      <div className="mt-3 text-sm text-gray-500">
        Confidence: {summary.confidence}%
      </div>
      {summary.key_metrics.length > 0 && (
        <div className="mt-3">
          <div className="text-sm font-medium text-gray-600">Key Metrics:</div>
          <div className="mt-1 flex flex-wrap gap-2">
            {summary.key_metrics.map((metric) => (
              <span
                key={metric}
                className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-700"
              >
                {metric.replace("_", " ")}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

