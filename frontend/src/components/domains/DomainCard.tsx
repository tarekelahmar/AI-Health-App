import React from 'react';
import { Link } from 'react-router-dom';
import { Sparkline } from '../ui/Sparkline';
import { Badge } from '../ui/Badge';

export interface DomainCardData {
  key: string;
  display_name: string;
  description: string;
  color: string;
  sparklineData: number[];
  currentValue?: string;
  unit?: string;
  status: 'no_data' | 'baseline_building' | 'no_signal' | 'signal_detected';
}

const statusConfig: Record<string, { label: string; variant: 'neutral' | 'info' | 'success' | 'warning' }> = {
  no_data: { label: 'No data', variant: 'neutral' },
  baseline_building: { label: 'Building baseline', variant: 'info' },
  no_signal: { label: 'Normal', variant: 'success' },
  signal_detected: { label: 'Signal detected', variant: 'warning' },
};

export function DomainCard({ domain }: { domain: DomainCardData }) {
  const cfg = statusConfig[domain.status] || statusConfig.no_data;

  return (
    <Link
      to={`/domains/${domain.key}`}
      className="block bg-white rounded-xl border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all overflow-hidden"
    >
      <div className="flex">
        {/* Color accent bar */}
        <div className="w-1 flex-shrink-0" style={{ backgroundColor: domain.color }} />
        <div className="flex-1 p-3">
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-sm font-semibold text-gray-900 truncate">{domain.display_name}</h3>
            <Badge variant={cfg.variant} size="sm">{cfg.label}</Badge>
          </div>
          <div className="flex items-end justify-between mt-2">
            {domain.currentValue ? (
              <div>
                <span className="text-lg font-bold text-gray-900">{domain.currentValue}</span>
                {domain.unit && <span className="text-xs text-gray-400 ml-0.5">{domain.unit}</span>}
              </div>
            ) : (
              <span className="text-xs text-gray-400">--</span>
            )}
            {domain.sparklineData.length > 0 && (
              <Sparkline data={domain.sparklineData} color={domain.color} width={80} height={28} />
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
