import React from "react";
import type { PersonalDriver } from "../types/PersonalDrivers";

interface PersonalDriversPanelProps {
  drivers: PersonalDriver[];
  loading?: boolean;
}

function formatDriverKey(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

function formatMetricKey(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

export default function PersonalDriversPanel({ drivers, loading }: PersonalDriversPanelProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg p-4 border border-gray-200">
        <div className="text-sm text-gray-500">Loading personal drivers...</div>
      </div>
    );
  }

  if (drivers.length === 0) {
    return (
      <div className="bg-white rounded-lg p-4 border border-gray-200">
        <div className="text-sm text-gray-500">No personal drivers identified yet.</div>
        <div className="text-xs text-gray-400 mt-1">
          Complete daily check-ins and track interventions to discover what affects your metrics.
        </div>
      </div>
    );
  }

  // Group by outcome metric
  const byOutcome: Record<string, PersonalDriver[]> = {};
  for (const d of drivers) {
    if (!byOutcome[d.outcome_metric]) {
      byOutcome[d.outcome_metric] = [];
    }
    byOutcome[d.outcome_metric].push(d);
  }

  // Separate into helping, hurting, unclear
  const helping: PersonalDriver[] = [];
  const hurting: PersonalDriver[] = [];
  const unclear: PersonalDriver[] = [];

  for (const d of drivers) {
    if (d.direction === "positive" && d.confidence >= 0.6) {
      helping.push(d);
    } else if (d.direction === "negative" && d.confidence >= 0.6) {
      hurting.push(d);
    } else {
      unclear.push(d);
    }
  }

  // Sort by confidence * abs(effect_size)
  helping.sort((a, b) => (b.confidence * b.effect_size) - (a.confidence * a.effect_size));
  hurting.sort((a, b) => (b.confidence * Math.abs(b.effect_size)) - (a.confidence * Math.abs(a.effect_size)));
  unclear.sort((a, b) => b.confidence - a.confidence);

  return (
    <div className="bg-white rounded-lg p-4 border border-gray-200 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Personal Drivers</h2>
        <div className="text-xs text-gray-500">{drivers.length} drivers</div>
      </div>

      {/* Disclaimer */}
      <div className="bg-blue-50 border border-blue-200 rounded p-2 text-xs text-gray-700">
        <strong>Personal attribution.</strong> These findings are specific to your data patterns. They show associations, not causation.
      </div>

      {/* What's helping */}
      {helping.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-green-800">What's helping you</h3>
          {helping.slice(0, 5).map((driver) => (
            <div key={driver.id} className="border border-green-200 rounded p-2 bg-green-50">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900">
                    {formatDriverKey(driver.driver_key)}
                  </div>
                  <div className="text-xs text-gray-600 mt-1">
                    → {formatMetricKey(driver.outcome_metric)}
                    {driver.lag_days > 0 && ` (${driver.lag_days} day lag)`}
                  </div>
                </div>
                <div className="text-xs text-green-700 font-medium">+</div>
              </div>
              <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
                <div>
                  <div className="text-gray-500">Effect</div>
                  <div className="font-medium text-gray-900">+{driver.effect_size.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-gray-500">Confidence</div>
                  <div className="font-medium text-gray-900">{(driver.confidence * 100).toFixed(0)}%</div>
                </div>
                <div>
                  <div className="text-gray-500">Variance</div>
                  <div className="font-medium text-gray-900">{(driver.variance_explained * 100).toFixed(0)}%</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* What's hurting */}
      {hurting.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-red-800">What's hurting you</h3>
          {hurting.slice(0, 5).map((driver) => (
            <div key={driver.id} className="border border-red-200 rounded p-2 bg-red-50">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900">
                    {formatDriverKey(driver.driver_key)}
                  </div>
                  <div className="text-xs text-gray-600 mt-1">
                    → {formatMetricKey(driver.outcome_metric)}
                    {driver.lag_days > 0 && ` (${driver.lag_days} day lag)`}
                  </div>
                </div>
                <div className="text-xs text-red-700 font-medium">-</div>
              </div>
              <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
                <div>
                  <div className="text-gray-500">Effect</div>
                  <div className="font-medium text-gray-900">{driver.effect_size.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-gray-500">Confidence</div>
                  <div className="font-medium text-gray-900">{(driver.confidence * 100).toFixed(0)}%</div>
                </div>
                <div>
                  <div className="text-gray-500">Variance</div>
                  <div className="font-medium text-gray-900">{(driver.variance_explained * 100).toFixed(0)}%</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Still unclear */}
      {unclear.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-gray-600">Still unclear</h3>
          {unclear.slice(0, 3).map((driver) => (
            <div key={driver.id} className="border border-gray-200 rounded p-2 bg-gray-50">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-700">
                    {formatDriverKey(driver.driver_key)}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    → {formatMetricKey(driver.outcome_metric)}
                    {driver.lag_days > 0 && ` (${driver.lag_days} day lag)`}
                  </div>
                </div>
                <div className="text-xs text-gray-500">?</div>
              </div>
              <div className="mt-2 text-xs text-gray-500">
                Confidence: {(driver.confidence * 100).toFixed(0)}% • Need more data
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

