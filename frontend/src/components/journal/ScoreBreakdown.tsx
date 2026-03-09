import React from 'react';
import { Card } from '../ui/Card';
import type { ContributingFactor } from '../../types/WellnessScore';

interface ScoreBreakdownProps {
  factors: ContributingFactor[];
}

export function ScoreBreakdown({ factors }: ScoreBreakdownProps) {
  if (!factors || factors.length === 0) {
    return null;
  }

  // Sort by impact (|z_score * weight|) descending
  const sorted = [...factors].sort((a, b) => Math.abs(b.z_score * b.weight) - Math.abs(a.z_score * a.weight));

  return (
    <Card>
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Score Breakdown</h3>
      <div className="space-y-2.5">
        {sorted.map((factor) => {
          const impact = factor.z_score * factor.weight;
          const isPositive = factor.direction === 'positive';
          const barWidth = Math.min(Math.abs(factor.z_score) / 2.5 * 100, 100);

          return (
            <div key={factor.metric_key}>
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-xs text-gray-600">{factor.label}</span>
                <div className="flex items-center gap-1.5">
                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                    factor.category === 'objective'
                      ? 'bg-blue-50 text-blue-600'
                      : 'bg-purple-50 text-purple-600'
                  }`}>
                    {factor.category === 'objective' ? 'Wearable' : 'Journal'}
                  </span>
                  <span className={`text-xs font-medium ${isPositive ? 'text-emerald-600' : 'text-red-500'}`}>
                    {isPositive ? '+' : ''}{factor.z_score.toFixed(1)}σ
                  </span>
                </div>
              </div>
              <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    isPositive ? 'bg-emerald-400' : 'bg-red-400'
                  }`}
                  style={{ width: `${barWidth}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex items-center gap-3 mt-3 pt-2 border-t border-gray-100">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-emerald-400" />
          <span className="text-[10px] text-gray-500">Above baseline</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-red-400" />
          <span className="text-[10px] text-gray-500">Below baseline</span>
        </div>
      </div>
    </Card>
  );
}
