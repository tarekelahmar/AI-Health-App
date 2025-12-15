import React from "react";
import type { DriverFinding } from "../types/Drivers";

interface DriversPanelProps {
  findings: DriverFinding[];
  loading?: boolean;
}

function directionColor(direction: string) {
  switch (direction) {
    case "improves":
      return "bg-green-100 text-green-800";
    case "worsens":
      return "bg-red-100 text-red-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

function formatExposureKey(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

export default function DriversPanel({ findings, loading }: DriversPanelProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg p-4 border border-gray-200">
        <div className="text-sm text-gray-500">Loading driver findings...</div>
      </div>
    );
  }

  if (findings.length === 0) {
    return (
      <div className="bg-white rounded-lg p-4 border border-gray-200">
        <div className="text-sm text-gray-500">No driver associations found yet.</div>
        <div className="text-xs text-gray-400 mt-1">
          Complete daily check-ins and track interventions to discover associations.
        </div>
      </div>
    );
  }

  // Group by metric or exposure
  const byMetric: Record<string, DriverFinding[]> = {};
  for (const f of findings) {
    if (!byMetric[f.metric_key]) {
      byMetric[f.metric_key] = [];
    }
    byMetric[f.metric_key].push(f);
  }

  return (
    <div className="bg-white rounded-lg p-4 border border-gray-200 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Driver Associations</h2>
        <div className="text-xs text-gray-500">{findings.length} findings</div>
      </div>

      {/* Disclaimer */}
      <div className="bg-yellow-50 border border-yellow-200 rounded p-2 text-xs text-gray-700">
        <strong>Association, not causation.</strong> These findings show correlations between your behaviors/interventions and metrics. They do not prove cause and effect.
      </div>

      {/* Findings grouped by metric */}
      {Object.entries(byMetric).map(([metricKey, metricFindings]) => (
        <div key={metricKey} className="space-y-2">
          <div className="text-sm font-medium text-gray-700">{metricKey.replace(/_/g, " ")}</div>
          {metricFindings.map((finding) => (
            <div
              key={finding.id}
              className="border border-gray-200 rounded p-3 space-y-2"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900">
                    {formatExposureKey(finding.exposure_key)}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {finding.exposure_type} • {finding.lag_days === 0 ? "same day" : `${finding.lag_days} day${finding.lag_days > 1 ? "s" : ""} lag`}
                  </div>
                </div>
                <span className={`text-xs px-2 py-1 rounded font-medium ${directionColor(finding.direction)}`}>
                  {finding.direction}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2 text-xs">
                <div>
                  <div className="text-gray-500">Effect size</div>
                  <div className="font-medium text-gray-900">
                    {finding.effect_size > 0 ? "+" : ""}{finding.effect_size.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-gray-500">Confidence</div>
                  <div className="font-medium text-gray-900">
                    {(finding.confidence * 100).toFixed(0)}%
                  </div>
                </div>
                <div>
                  <div className="text-gray-500">Coverage</div>
                  <div className="font-medium text-gray-900">
                    {(finding.coverage * 100).toFixed(0)}%
                  </div>
                </div>
              </div>

              <div className="text-xs text-gray-500">
                Based on {finding.n_exposure_days} exposure days out of {finding.n_total_days} total days
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

