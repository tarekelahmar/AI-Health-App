import React from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';

export interface CrossDomainCorrelation {
  source_domain: string;
  target_domain: string;
  metric_x: string;
  metric_y: string;
  best_lag_days: number;
  correlation: number;
  p_value: number;
  mechanism?: string;
  confidence: number;
}

interface CrossDomainCardProps {
  correlations: CrossDomainCorrelation[];
}

function strengthLabel(r: number): { label: string; variant: 'success' | 'info' | 'warning' } {
  const abs = Math.abs(r);
  if (abs >= 0.7) return { label: 'strong', variant: 'success' };
  if (abs >= 0.4) return { label: 'moderate', variant: 'info' };
  return { label: 'weak', variant: 'warning' };
}

export function CrossDomainCard({ correlations }: CrossDomainCardProps) {
  if (correlations.length === 0) return null;

  return (
    <Card>
      <h3 className="text-sm font-semibold text-gray-900 mb-3">Cross-Domain Relationships</h3>
      <div className="space-y-3">
        {correlations.map((c, i) => {
          const strength = strengthLabel(c.correlation);
          return (
            <div key={i} className="flex flex-col gap-1">
              <div className="flex items-center gap-2 text-sm">
                <span className="font-medium text-gray-800">
                  {c.metric_x.replace(/_/g, ' ')}
                </span>
                <span className="text-gray-400">&rarr;</span>
                <span className="text-gray-600">
                  {c.metric_y.replace(/_/g, ' ')}
                </span>
                <Badge variant={strength.variant} size="sm">{strength.label}</Badge>
              </div>
              <div className="flex items-center gap-3 text-[10px] text-gray-400">
                <span>r = {c.correlation.toFixed(2)}</span>
                <span>lag: {c.best_lag_days}d</span>
                <span>p = {c.p_value.toFixed(3)}</span>
                <span>conf: {Math.round(c.confidence * 100)}%</span>
              </div>
              {c.mechanism && (
                <p className="text-xs text-gray-500 italic">{c.mechanism}</p>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}
