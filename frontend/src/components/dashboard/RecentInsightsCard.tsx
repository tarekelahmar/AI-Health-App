import React from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';

export interface InsightSummary {
  id: number;
  title: string;
  domain: string;
  severity: string;
  created_at: string;
}

interface RecentInsightsCardProps {
  insights: InsightSummary[];
}

const severityVariant: Record<string, 'info' | 'success' | 'warning' | 'danger' | 'neutral'> = {
  info: 'info',
  low: 'neutral',
  medium: 'warning',
  high: 'danger',
  observation: 'info',
  pattern: 'info',
  advisory: 'warning',
  alert: 'danger',
};

export function RecentInsightsCard({ insights }: RecentInsightsCardProps) {
  return (
    <Card>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-900">Recent Insights</h3>
        <Link
          to="/insights"
          className="text-xs font-medium text-primary-600 hover:text-primary-700"
        >
          View all
        </Link>
      </div>
      {insights.length === 0 ? (
        <p className="text-xs text-gray-400 py-4 text-center">No recent insights</p>
      ) : (
        <div className="space-y-2.5">
          {insights.slice(0, 3).map((insight) => (
            <div key={insight.id} className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <p className="text-sm text-gray-800 truncate">{insight.title}</p>
                <p className="text-[10px] text-gray-400 mt-0.5">
                  {insight.domain} &middot; {new Date(insight.created_at).toLocaleDateString()}
                </p>
              </div>
              <Badge
                variant={severityVariant[insight.severity] || 'neutral'}
                size="sm"
              >
                {insight.severity}
              </Badge>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
