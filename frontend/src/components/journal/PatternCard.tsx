import React from 'react';
import type { JournalPatternData } from '../../types/JournalFactors';

interface PatternCardProps {
  pattern: JournalPatternData;
}

export function PatternCard({ pattern }: PatternCardProps) {
  const maxBar = Math.max(pattern.mean_with, pattern.mean_without, 1);
  const withPct = (pattern.mean_with / 10) * 100;
  const withoutPct = (pattern.mean_without / 10) * 100;

  const statusColor = pattern.status === 'confirmed'
    ? 'bg-emerald-100 text-emerald-700'
    : pattern.status === 'hypothesis'
    ? 'bg-amber-100 text-amber-700'
    : 'bg-gray-100 text-gray-500';

  const statusLabel = pattern.status === 'confirmed'
    ? 'Confirmed'
    : pattern.status === 'hypothesis'
    ? 'Hypothesis'
    : pattern.status;

  // Color for the "with" bar based on pattern type
  const barColor = pattern.pattern_type === 'crash'
    ? 'bg-red-400'
    : pattern.pattern_type === 'boost'
    ? 'bg-blue-400'
    : 'bg-emerald-400';

  return (
    <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm">
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">{pattern.icon}</span>
          <div>
            <h4 className="text-sm font-semibold text-gray-800">{pattern.pattern_name}</h4>
            <span className="text-[10px] text-gray-400 uppercase">
              {pattern.output_metric.replace('_', ' ')}
            </span>
          </div>
        </div>
        <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${statusColor}`}>
          {statusLabel}
        </span>
      </div>

      {/* Description */}
      <p className="text-xs text-gray-500 mb-3">{pattern.description}</p>

      {/* Evidence bars */}
      <div className="space-y-1.5 mb-3">
        <div>
          <div className="flex items-center justify-between text-[10px] text-gray-500 mb-0.5">
            <span>With factor{pattern.input_factors.length > 1 ? 's' : ''}</span>
            <span className="font-medium">{pattern.mean_with}</span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${barColor}`}
              style={{ width: `${withPct}%` }}
            />
          </div>
        </div>
        <div>
          <div className="flex items-center justify-between text-[10px] text-gray-500 mb-0.5">
            <span>Without</span>
            <span className="font-medium">{pattern.mean_without}</span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-gray-300"
              style={{ width: `${withoutPct}%` }}
            />
          </div>
        </div>
      </div>

      {/* Factor tags */}
      <div className="flex flex-wrap gap-1">
        {pattern.input_factors.map((f) => (
          <span
            key={f}
            className="text-[10px] px-2 py-0.5 rounded-full bg-gray-50 text-gray-500 border border-gray-100"
          >
            {f.replace(/_/g, ' ')}
          </span>
        ))}
      </div>

      {/* Stats footer */}
      <div className="flex items-center gap-3 mt-3 pt-2 border-t border-gray-50 text-[10px] text-gray-400">
        <span>Effect: {pattern.effect_size.toFixed(1)}d</span>
        <span>{pattern.n_observations} observations</span>
        {pattern.exceptions > 0 && <span>{pattern.exceptions} exceptions</span>}
      </div>
    </div>
  );
}
