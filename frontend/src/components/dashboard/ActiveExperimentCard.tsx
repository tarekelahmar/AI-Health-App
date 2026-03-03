import React from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { ProgressBar } from '../ui/ProgressBar';

export interface ActiveExperiment {
  id: number;
  name: string;
  phase: string;
  progress_pct: number;
  days_remaining: number;
  adherence_rate: number;
}

interface ActiveExperimentCardProps {
  experiments: ActiveExperiment[];
}

const phaseBadgeVariant: Record<string, 'info' | 'success' | 'warning' | 'neutral'> = {
  baseline: 'neutral',
  intervention: 'info',
  washout: 'warning',
  analysis: 'success',
};

export function ActiveExperimentCard({ experiments }: ActiveExperimentCardProps) {
  if (experiments.length === 0) return null;

  return (
    <Card>
      <h3 className="text-sm font-semibold text-gray-900 mb-3">Active Experiments</h3>
      <div className="space-y-4">
        {experiments.slice(0, 2).map((exp) => (
          <div key={exp.id}>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-sm font-medium text-gray-800">{exp.name}</span>
              <Badge
                variant={phaseBadgeVariant[exp.phase] || 'neutral'}
                size="sm"
              >
                {exp.phase}
              </Badge>
            </div>
            <ProgressBar
              value={exp.progress_pct}
              max={100}
              showPercent
              size="sm"
            />
            <div className="flex items-center justify-between mt-1.5">
              <span className="text-[10px] text-gray-400">
                {exp.days_remaining} days remaining
              </span>
              <span className={`text-[10px] font-medium ${
                exp.adherence_rate >= 80 ? 'text-emerald-600' : 'text-amber-600'
              }`}>
                {Math.round(exp.adherence_rate)}% adherence
              </span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
