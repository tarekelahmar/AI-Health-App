import React from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import type { RiskAssessment } from '../../types/Risk';

interface RiskAlertCardProps {
  assessments: RiskAssessment[];
}

const riskBadgeVariant: Record<string, 'danger' | 'warning' | 'info' | 'neutral'> = {
  high: 'danger',
  elevated: 'warning',
  moderate: 'info',
  low: 'neutral',
};

const riskTypeLabels: Record<string, string> = {
  illness_vulnerability: 'Illness Risk',
  burnout_trajectory: 'Burnout Risk',
  overtraining_risk: 'Overtraining',
  sleep_debt: 'Sleep Debt',
};

export function RiskAlertCard({ assessments }: RiskAlertCardProps) {
  const elevated = assessments.filter((a) => a.risk_level !== 'low');
  if (elevated.length === 0) return null;

  return (
    <Card>
      <h3 className="text-sm font-semibold text-gray-900 mb-3">Risk Alerts</h3>
      <div className="space-y-3">
        {elevated.slice(0, 2).map((a) => (
          <div key={a.risk_type} className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-800">
                {riskTypeLabels[a.risk_type] || a.risk_type}
              </span>
              <Badge
                variant={riskBadgeVariant[a.risk_level] || 'neutral'}
                size="sm"
              >
                {a.risk_level}
              </Badge>
            </div>
            <p className="text-xs text-gray-500 leading-relaxed">{a.description}</p>
            {a.recommended_actions.length > 0 && (
              <ul className="mt-1 space-y-0.5">
                {a.recommended_actions.slice(0, 2).map((action, i) => (
                  <li key={i} className="text-xs text-gray-600 flex items-start gap-1.5">
                    <span className="text-primary-500 mt-0.5 flex-shrink-0">-</span>
                    {action}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}
