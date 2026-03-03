import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Card } from '../components/ui/Card';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Badge } from '../components/ui/Badge';
import { MetricChart } from '../components/MetricChart';
import { CrossDomainCard, CrossDomainCorrelation } from '../components/domains/CrossDomainCard';
import { fetchHealthDomain } from '../api/healthDomains';
import { fetchMetricSeries } from '../api/metrics';
import { fetchInsightsFeed } from '../api/insights';
import apiClient from '../api/client';
import type { HealthDomainInfo } from '../types/HealthDomain';
import type { MetricSeriesResponse } from '../types/MetricSeries';

// Map domain keys to their primary metrics for charting
const DOMAIN_METRICS: Record<string, { key: string; label: string }[]> = {
  sleep: [
    { key: 'sleep_duration_minutes', label: 'Sleep Duration' },
    { key: 'sleep_efficiency_pct', label: 'Sleep Efficiency' },
  ],
  stress_nervous_system: [
    { key: 'hrv_rmssd_ms', label: 'HRV (RMSSD)' },
    { key: 'resting_heart_rate_bpm', label: 'Resting Heart Rate' },
  ],
  energy_fatigue: [
    { key: 'subjective_energy', label: 'Subjective Energy' },
  ],
  cardiometabolic: [
    { key: 'resting_heart_rate_bpm', label: 'Resting Heart Rate' },
  ],
  inflammation_immune: [
    { key: 'respiratory_rate_brpm', label: 'Respiratory Rate' },
  ],
};

const DOMAIN_COLORS: Record<string, string> = {
  sleep: '#6366f1',
  stress_nervous_system: '#8b5cf6',
  energy_fatigue: '#f59e0b',
  cardiometabolic: '#ef4444',
  gastrointestinal: '#22c55e',
  inflammation_immune: '#f97316',
  hormonal_reproductive: '#ec4899',
  cognitive_mental_performance: '#3b82f6',
  musculoskeletal_recovery: '#14b8a6',
  nutrition_micronutrients: '#84cc16',
};

export default function DomainDetailPage() {
  const { key } = useParams<{ key: string }>();
  const { userId } = useAuth();
  const [loading, setLoading] = useState(true);
  const [domain, setDomain] = useState<HealthDomainInfo | null>(null);
  const [metricSeries, setMetricSeries] = useState<{ label: string; series: MetricSeriesResponse }[]>([]);
  const [insights, setInsights] = useState<any[]>([]);
  const [correlations, setCorrelations] = useState<CrossDomainCorrelation[]>([]);

  useEffect(() => {
    if (!key || !userId) return;
    loadDomainDetail();
  }, [key, userId]);

  const loadDomainDetail = async () => {
    if (!key || !userId) return;
    setLoading(true);

    try {
      // Fetch domain info and metrics in parallel
      const [domainInfo, insightsRes] = await Promise.allSettled([
        fetchHealthDomain(key),
        fetchInsightsFeed(userId, 50),
      ]);

      if (domainInfo.status === 'fulfilled') {
        setDomain(domainInfo.value);
      }

      // Filter insights for this domain
      if (insightsRes.status === 'fulfilled') {
        const allInsights = insightsRes.value.items || [];
        const domainInsights = allInsights.filter((i: any) => i.domain_key === key);
        setInsights(domainInsights.slice(0, 5));
      }

      // Fetch metric series for this domain
      const metricsConfig = DOMAIN_METRICS[key] || [];
      const seriesResults = await Promise.allSettled(
        metricsConfig.map(async (m) => {
          const series = await fetchMetricSeries(userId, m.key);
          return { label: m.label, series };
        })
      );

      const successfulSeries = seriesResults
        .filter((r): r is PromiseFulfilledResult<{ label: string; series: MetricSeriesResponse }> =>
          r.status === 'fulfilled'
        )
        .map((r) => r.value);

      setMetricSeries(successfulSeries);

      // Fetch cross-domain correlations
      try {
        const corrRes = await apiClient.get('/correlations/cross-domain');
        const allCorrs = corrRes.data.correlations || [];
        // Filter correlations relevant to this domain
        const relevant = allCorrs.filter(
          (c: CrossDomainCorrelation) => c.source_domain === key || c.target_domain === key
        );
        setCorrelations(relevant);
      } catch {
        // Non-blocking - correlations are optional
      }
    } catch (error) {
      console.error('Failed to load domain detail', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <LoadingSpinner label="Loading domain data..." />;
  }

  const displayName = domain?.display_name || key?.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) || '';
  const color = DOMAIN_COLORS[key || ''] || '#6b7280';

  return (
    <div className="space-y-4">
      {/* Back link + header */}
      <div>
        <Link to="/domains" className="text-xs text-primary-600 hover:text-primary-700 font-medium">
          &larr; All domains
        </Link>
        <div className="flex items-center gap-2 mt-2">
          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
          <h1 className="text-xl font-bold text-gray-900">{displayName}</h1>
        </div>
        {domain?.description && (
          <p className="text-sm text-gray-500 mt-1">{domain.description}</p>
        )}
      </div>

      {/* Metric charts */}
      {metricSeries.length > 0 ? (
        <div className="space-y-4">
          {metricSeries.map(({ label, series }) => (
            <MetricChart key={label} series={series} title={label} />
          ))}
        </div>
      ) : (
        <Card>
          <p className="text-sm text-gray-500 text-center py-6">
            No metric data available for this domain yet.
          </p>
        </Card>
      )}

      {/* Domain insights */}
      <Card>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Domain Insights</h3>
        {insights.length === 0 ? (
          <p className="text-xs text-gray-400 text-center py-4">No insights for this domain yet.</p>
        ) : (
          <div className="space-y-2.5">
            {insights.map((insight: any) => (
              <div key={insight.id} className="border-b border-gray-100 last:border-0 pb-2 last:pb-0">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm text-gray-800">{insight.title || insight.summary}</p>
                  <Badge variant="info" size="sm">{insight.claim_level || insight.status}</Badge>
                </div>
                {insight.summary && insight.title && (
                  <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{insight.summary}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Cross-domain correlations */}
      <CrossDomainCard correlations={correlations} />

      {/* Example signals */}
      {domain?.example_signals && domain.example_signals.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-900 mb-2">Tracked Signals</h3>
          <div className="flex flex-wrap gap-1.5">
            {domain.example_signals.map((s) => (
              <span key={s} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                {s.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
