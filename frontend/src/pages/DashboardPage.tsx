import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Card } from '../components/ui/Card';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { SectionHeader } from '../components/ui/SectionHeader';
import { RegimeBanner } from '../components/dashboard/RegimeBanner';
import { MetricSparklineRow } from '../components/dashboard/MetricSparklineRow';
import { RiskAlertCard } from '../components/dashboard/RiskAlertCard';
import { RiskOverview } from '../components/dashboard/RiskOverview';
import { ActiveExperimentCard, ActiveExperiment } from '../components/dashboard/ActiveExperimentCard';
import { RecentInsightsCard, InsightSummary } from '../components/dashboard/RecentInsightsCard';
import { fetchRiskAssessment } from '../api/risk';
import { fetchCurrentRegime } from '../api/regime';
import { fetchInsightsFeed } from '../api/insights';
import { fetchMetricSeries } from '../api/metrics';
import apiClient from '../api/client';
import type { RiskAssessment } from '../types/Risk';
import type { RegimeClassification } from '../types/Regime';

interface DashboardData {
  regime: RegimeClassification | null;
  risks: RiskAssessment[];
  insights: InsightSummary[];
  experiments: ActiveExperiment[];
  sparklines: {
    hrv: number[];
    sleep: number[];
    energy: number[];
    rhr: number[];
  };
  currentValues: {
    hrv?: string;
    sleep?: string;
    energy?: string;
    rhr?: string;
  };
}

function computeTrend(data: number[]): 'up' | 'down' | 'stable' {
  if (data.length < 3) return 'stable';
  const recent = data.slice(-3);
  const avg = recent.reduce((a, b) => a + b, 0) / recent.length;
  const earlier = data.slice(-6, -3);
  if (earlier.length === 0) return 'stable';
  const earlyAvg = earlier.reduce((a, b) => a + b, 0) / earlier.length;
  const pctChange = ((avg - earlyAvg) / (earlyAvg || 1)) * 100;
  if (Math.abs(pctChange) < 3) return 'stable';
  return pctChange > 0 ? 'up' : 'down';
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { userId } = useAuth();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<DashboardData>({
    regime: null,
    risks: [],
    insights: [],
    experiments: [],
    sparklines: { hrv: [], sleep: [], energy: [], rhr: [] },
    currentValues: {},
  });

  useEffect(() => {
    if (!userId) {
      navigate('/login');
      return;
    }
    loadDashboard();
  }, [userId]);

  const loadDashboard = async () => {
    if (!userId) return;
    setLoading(true);

    // Fetch all data in parallel - each call is independent and non-blocking
    const [regimeResult, riskResult, insightsResult, experimentsResult, hrvData, sleepData, energyData, rhrData] =
      await Promise.allSettled([
        fetchCurrentRegime(),
        fetchRiskAssessment(),
        fetchInsightsFeed(userId, 3),
        apiClient.get('/experiments', { params: { limit: 5 } }).then((r) => r.data),
        fetchMetricSeries(userId, 'hrv_rmssd_ms').catch(() => null),
        fetchMetricSeries(userId, 'sleep_duration_minutes').catch(() => null),
        fetchMetricSeries(userId, 'subjective_energy').catch(() => null),
        fetchMetricSeries(userId, 'resting_heart_rate_bpm').catch(() => null),
      ]);

    const regime = regimeResult.status === 'fulfilled' ? regimeResult.value : null;
    const risks = riskResult.status === 'fulfilled' ? riskResult.value.assessments || [] : [];

    // Transform insights to summary format
    const rawInsights = insightsResult.status === 'fulfilled' ? insightsResult.value.items || [] : [];
    const insights: InsightSummary[] = rawInsights.map((i: any) => ({
      id: i.id,
      title: i.title || i.summary?.slice(0, 60) || 'Insight',
      domain: i.domain_key || 'general',
      severity: i.claim_level || i.status || 'info',
      created_at: i.created_at || new Date().toISOString(),
    }));

    // Transform experiments
    const rawExperiments = experimentsResult.status === 'fulfilled' ? experimentsResult.value : [];
    const activeExps: ActiveExperiment[] = (Array.isArray(rawExperiments) ? rawExperiments : rawExperiments.items || [])
      .filter((e: any) => e.status === 'active' || e.status === 'running')
      .slice(0, 2)
      .map((e: any) => ({
        id: e.id,
        name: e.name || e.intervention_key || 'Experiment',
        phase: e.current_phase || 'intervention',
        progress_pct: e.progress_pct || 0,
        days_remaining: e.days_remaining || 0,
        adherence_rate: e.adherence_rate || 0,
      }));

    // Extract sparkline data from metric series
    const extractValues = (result: PromiseSettledResult<any>): number[] => {
      if (result.status !== 'fulfilled' || !result.value) return [];
      const points = result.value.points || [];
      return points.slice(-7).map((p: any) => p.value);
    };

    const extractCurrent = (result: PromiseSettledResult<any>): string | undefined => {
      if (result.status !== 'fulfilled' || !result.value) return undefined;
      const points = result.value.points || [];
      if (points.length === 0) return undefined;
      const val = points[points.length - 1].value;
      return typeof val === 'number' ? Math.round(val).toString() : String(val);
    };

    setData({
      regime,
      risks,
      insights,
      experiments: activeExps,
      sparklines: {
        hrv: extractValues(hrvData),
        sleep: extractValues(sleepData),
        energy: extractValues(energyData),
        rhr: extractValues(rhrData),
      },
      currentValues: {
        hrv: extractCurrent(hrvData),
        sleep: extractCurrent(sleepData),
        energy: extractCurrent(energyData),
        rhr: extractCurrent(rhrData),
      },
    });

    setLoading(false);
  };

  if (loading) {
    return <LoadingSpinner label="Loading dashboard..." />;
  }

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  const sparklineMetrics = [
    ...(data.sparklines.hrv.length > 0
      ? [{
          label: 'HRV',
          value: data.currentValues.hrv || '--',
          unit: 'ms',
          data: data.sparklines.hrv,
          color: '#0d9488',
          trend: computeTrend(data.sparklines.hrv),
        }]
      : []),
    ...(data.sparklines.sleep.length > 0
      ? [{
          label: 'Sleep',
          value: data.currentValues.sleep || '--',
          unit: 'min',
          data: data.sparklines.sleep,
          color: '#6366f1',
          trend: computeTrend(data.sparklines.sleep),
        }]
      : []),
    ...(data.sparklines.energy.length > 0
      ? [{
          label: 'Energy',
          value: data.currentValues.energy || '--',
          unit: '/5',
          data: data.sparklines.energy,
          color: '#f59e0b',
          trend: computeTrend(data.sparklines.energy),
        }]
      : []),
    ...(data.sparklines.rhr.length > 0
      ? [{
          label: 'RHR',
          value: data.currentValues.rhr || '--',
          unit: 'bpm',
          data: data.sparklines.rhr,
          color: '#ef4444',
          trend: computeTrend(data.sparklines.rhr) as 'up' | 'down' | 'stable',
        }]
      : []),
  ];

  return (
    <div className="space-y-4">
      {/* Date header */}
      <div>
        <h1 className="text-xl font-bold text-gray-900">Good morning</h1>
        <p className="text-sm text-gray-500">{today}</p>
      </div>

      {/* Regime banner (conditional) */}
      {data.regime && data.regime.regime !== 'normal' && (
        <RegimeBanner regime={data.regime.regime} context={data.regime.context} />
      )}

      {/* Daily metrics sparklines */}
      {sparklineMetrics.length > 0 && (
        <Card>
          <SectionHeader title="Today's Metrics" subtitle="7-day trend" />
          <MetricSparklineRow metrics={sparklineMetrics} />
        </Card>
      )}

      {/* Risk alerts - overview grid for all types, condensed alerts for top risks */}
      {data.risks.length >= 4 ? (
        <RiskOverview assessments={data.risks} />
      ) : (
        <RiskAlertCard assessments={data.risks} />
      )}

      {/* Active experiments (conditional) */}
      <ActiveExperimentCard experiments={data.experiments} />

      {/* Recent insights */}
      <RecentInsightsCard insights={data.insights} />

      {/* Quick actions */}
      <div className="grid grid-cols-2 gap-3">
        <Link
          to="/insights"
          className="flex items-center justify-center gap-2 bg-white border border-gray-200 rounded-xl py-3 px-4 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-4 h-4">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" />
          </svg>
          All Insights
        </Link>
        <Link
          to="/narratives"
          className="flex items-center justify-center gap-2 bg-white border border-gray-200 rounded-xl py-3 px-4 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-4 h-4">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
          Narratives
        </Link>
      </div>
    </div>
  );
}
