import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { DomainCard, DomainCardData } from '../components/domains/DomainCard';
import { fetchHealthDomains } from '../api/healthDomains';
import { fetchMetricSeries } from '../api/metrics';

// Map domain keys to their color hex values and primary metric
const DOMAIN_CONFIG: Record<string, { color: string; metric?: string; unit?: string }> = {
  sleep: { color: '#6366f1', metric: 'sleep_duration_minutes', unit: 'min' },
  stress_nervous_system: { color: '#8b5cf6', metric: 'hrv_rmssd_ms', unit: 'ms' },
  energy_fatigue: { color: '#f59e0b', metric: 'subjective_energy', unit: '/5' },
  cardiometabolic: { color: '#ef4444', metric: 'resting_heart_rate_bpm', unit: 'bpm' },
  gastrointestinal: { color: '#22c55e' },
  inflammation_immune: { color: '#f97316', metric: 'respiratory_rate_brpm', unit: 'brpm' },
  hormonal_reproductive: { color: '#ec4899' },
  cognitive_mental_performance: { color: '#3b82f6' },
  musculoskeletal_recovery: { color: '#14b8a6' },
  nutrition_micronutrients: { color: '#84cc16' },
};

export default function DomainsPage() {
  const navigate = useNavigate();
  const { userId } = useAuth();
  const [loading, setLoading] = useState(true);
  const [domains, setDomains] = useState<DomainCardData[]>([]);

  useEffect(() => {
    if (!userId) {
      navigate('/login');
      return;
    }
    loadDomains();
  }, [userId]);

  const loadDomains = async () => {
    if (!userId) return;
    setLoading(true);

    try {
      const domainsRes = await fetchHealthDomains();
      const items = domainsRes.items || [];

      // Fetch metric data in parallel for domains that have a primary metric
      const metricPromises = items.map(async (d): Promise<DomainCardData> => {
        const cfg = DOMAIN_CONFIG[d.key] || { color: '#6b7280' };
        let sparklineData: number[] = [];
        let currentValue: string | undefined;
        let status: DomainCardData['status'] = 'no_data';

        if (cfg.metric) {
          try {
            const series = await fetchMetricSeries(userId!, cfg.metric);
            const points = series.points || [];
            if (points.length > 0) {
              sparklineData = points.slice(-14).map((p: any) => p.value);
              const lastVal = points[points.length - 1].value;
              currentValue = typeof lastVal === 'number' ? Math.round(lastVal).toString() : String(lastVal);

              if (series.baseline?.available) {
                status = sparklineData.length >= 7 ? 'no_signal' : 'baseline_building';
              } else {
                status = points.length >= 5 ? 'baseline_building' : 'no_data';
              }
            }
          } catch {
            // Metric not available for this domain
          }
        }

        return {
          key: d.key,
          display_name: d.display_name,
          description: d.description,
          color: cfg.color,
          sparklineData,
          currentValue,
          unit: cfg.unit,
          status,
        };
      });

      const results = await Promise.all(metricPromises);
      setDomains(results);
    } catch (error) {
      console.error('Failed to load domains', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <LoadingSpinner label="Loading health domains..." />;
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Health Domains</h1>
        <p className="text-sm text-gray-500 mt-0.5">10 areas of your health, tracked over time</p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {domains.map((d) => (
          <DomainCard key={d.key} domain={d} />
        ))}
      </div>
    </div>
  );
}
