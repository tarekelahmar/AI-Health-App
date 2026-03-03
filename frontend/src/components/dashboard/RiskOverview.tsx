import React, { useState } from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { ProgressBar } from '../ui/ProgressBar';
import type { RiskAssessment, ContributingFactor } from '../../types/Risk';

interface RiskOverviewProps {
  assessments: RiskAssessment[];
}

const riskBadgeVariant: Record<string, 'danger' | 'warning' | 'info' | 'neutral' | 'success'> = {
  high: 'danger',
  elevated: 'warning',
  moderate: 'info',
  low: 'success',
};

const riskTypeLabels: Record<string, string> = {
  illness_vulnerability: 'Illness',
  burnout_trajectory: 'Burnout',
  overtraining_risk: 'Overtraining',
  sleep_debt: 'Sleep Debt',
};

function scoreToVariant(score: number): 'danger' | 'warning' | 'success' | 'default' {
  if (score >= 0.75) return 'danger';
  if (score >= 0.55) return 'warning';
  if (score >= 0.3) return 'default';
  return 'success';
}

export function RiskOverview({ assessments }: RiskOverviewProps) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (assessments.length === 0) return null;

  return (
    <Card>
      <h3 className="text-sm font-semibold text-gray-900 mb-3">Risk Overview</h3>

      {/* 2x2 grid of all 4 risk types */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        {assessments.map((a) => (
          <button
            key={a.risk_type}
            onClick={() => setExpanded(expanded === a.risk_type ? null : a.risk_type)}
            className={`text-left p-2.5 rounded-lg border transition-colors ${
              expanded === a.risk_type
                ? 'border-primary-300 bg-primary-50'
                : 'border-gray-100 bg-gray-50 hover:bg-gray-100'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-gray-700">
                {riskTypeLabels[a.risk_type] || a.risk_type}
              </span>
              <Badge variant={riskBadgeVariant[a.risk_level] || 'neutral'} size="sm">
                {a.risk_level}
              </Badge>
            </div>
            <ProgressBar
              value={Math.round(a.risk_score * 100)}
              max={100}
              size="sm"
              variant={scoreToVariant(a.risk_score)}
            />
          </button>
        ))}
      </div>

      {/* Expanded detail panel */}
      {expanded && (
        <RiskDetailPanel
          assessment={assessments.find((a) => a.risk_type === expanded)!}
        />
      )}
    </Card>
  );
}

function RiskDetailPanel({ assessment }: { assessment: RiskAssessment }) {
  return (
    <div className="border-t border-gray-100 pt-3 mt-1">
      <p className="text-sm text-gray-700 mb-3">{assessment.description}</p>

      {/* Contributing factors */}
      {assessment.contributing_factors.length > 0 && (
        <div className="mb-3">
          <h4 className="text-xs font-medium text-gray-500 mb-2">Contributing Factors</h4>
          <div className="space-y-1.5">
            {assessment.contributing_factors.map((f) => (
              <ContributingFactorBar key={f.metric} factor={f} />
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {assessment.recommended_actions.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-gray-500 mb-1.5">Recommendations</h4>
          <ul className="space-y-1">
            {assessment.recommended_actions.map((action, i) => (
              <li key={i} className="text-xs text-gray-600 flex items-start gap-1.5">
                <span className="text-primary-500 mt-0.5 flex-shrink-0">-</span>
                {action}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ContributingFactorBar({ factor }: { factor: ContributingFactor }) {
  const pct = Math.min(100, Math.abs(factor.deviation_pct));
  const isAdverse = (factor.direction === 'above' && factor.deviation_pct > 0) ||
                    (factor.direction === 'below' && factor.deviation_pct < 0);

  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-gray-500 w-24 truncate">
        {factor.metric.replace(/_/g, ' ')}
      </span>
      <div className="flex-1 bg-gray-100 rounded-full h-1.5">
        <div
          className={`h-1.5 rounded-full transition-all ${
            isAdverse ? 'bg-red-400' : 'bg-emerald-400'
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-[10px] font-medium w-16 text-right ${
        isAdverse ? 'text-red-500' : 'text-emerald-600'
      }`}>
        {factor.deviation_pct > 0 ? '+' : ''}{factor.deviation_pct.toFixed(0)}%
      </span>
    </div>
  );
}
