import React from 'react';
import { Sparkline } from '../ui/Sparkline';

interface MetricSparklineItem {
  label: string;
  value: string;
  unit: string;
  data: number[];
  color: string;
  trend?: 'up' | 'down' | 'stable';
}

interface MetricSparklineRowProps {
  metrics: MetricSparklineItem[];
}

export function MetricSparklineRow({ metrics }: MetricSparklineRowProps) {
  if (metrics.length === 0) return null;

  return (
    <div className="grid grid-cols-2 gap-3">
      {metrics.map((m) => (
        <div key={m.label} className="bg-gray-50 rounded-lg p-3">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-gray-500">{m.label}</span>
            {m.trend && m.trend !== 'stable' && (
              <span className={`text-[10px] font-medium ${
                m.trend === 'up' ? 'text-emerald-600' : 'text-red-500'
              }`}>
                {m.trend === 'up' ? '\u2191' : '\u2193'}
              </span>
            )}
          </div>
          <div className="flex items-end justify-between">
            <div>
              <span className="text-lg font-semibold text-gray-900">{m.value}</span>
              <span className="text-xs text-gray-400 ml-0.5">{m.unit}</span>
            </div>
            <Sparkline data={m.data} color={m.color} width={72} height={28} />
          </div>
        </div>
      ))}
    </div>
  );
}
