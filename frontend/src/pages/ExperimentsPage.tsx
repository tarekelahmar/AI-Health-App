import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { ProgressBar } from '../components/ui/ProgressBar';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { EmptyState } from '../components/ui/EmptyState';
import apiClient from '../api/client';

type Tab = 'active' | 'completed' | 'design';

interface Experiment {
  id: number;
  name?: string;
  intervention_id?: number;
  primary_metric_key?: string;
  status: string;
  started_at?: string;
  ended_at?: string;
  baseline_days?: number;
  intervention_days?: number;
}

const verdictConfig: Record<string, { label: string; variant: 'success' | 'neutral' | 'warning' | 'danger' }> = {
  helpful: { label: 'Helpful', variant: 'success' },
  not_helpful: { label: 'Not helpful', variant: 'neutral' },
  unclear: { label: 'Unclear', variant: 'warning' },
  insufficient_data: { label: 'Insufficient data', variant: 'neutral' },
};

export default function ExperimentsPage() {
  const navigate = useNavigate();
  const { userId } = useAuth();
  const [tab, setTab] = useState<Tab>('active');
  const [loading, setLoading] = useState(true);
  const [experiments, setExperiments] = useState<Experiment[]>([]);

  useEffect(() => {
    if (!userId) {
      navigate('/login');
      return;
    }
    loadExperiments();
  }, [userId]);

  const loadExperiments = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/experiments', { params: { limit: 100 } });
      setExperiments(Array.isArray(res.data) ? res.data : res.data.items || []);
    } catch (error) {
      console.error('Failed to load experiments', error);
    } finally {
      setLoading(false);
    }
  };

  const active = experiments.filter((e) => e.status === 'active' || e.status === 'running');
  const completed = experiments.filter((e) => e.status === 'completed' || e.status === 'stopped');

  const computeProgress = (exp: Experiment): number => {
    if (!exp.started_at) return 0;
    const start = new Date(exp.started_at).getTime();
    const totalDays = (exp.baseline_days || 14) + (exp.intervention_days || 21);
    const elapsed = (Date.now() - start) / (1000 * 60 * 60 * 24);
    return Math.min(100, Math.round((elapsed / totalDays) * 100));
  };

  if (loading) {
    return <LoadingSpinner label="Loading experiments..." />;
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Experiments</h1>
        <p className="text-sm text-gray-500 mt-0.5">N-of-1 experiments to test what works for you</p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-0.5">
        {(['active', 'completed', 'design'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 py-2 text-xs font-medium rounded-md transition-colors ${
              tab === t
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'active' ? `Active (${active.length})` : t === 'completed' ? `Completed (${completed.length})` : 'Design New'}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'active' && (
        active.length === 0 ? (
          <EmptyState
            title="No active experiments"
            message="Start an experiment to test how interventions affect your health metrics."
          />
        ) : (
          <div className="space-y-3">
            {active.map((exp) => {
              const progress = computeProgress(exp);
              return (
                <Card key={exp.id}>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-semibold text-gray-900">
                      {exp.name || `Experiment #${exp.id}`}
                    </h3>
                    <Badge variant="info" size="sm">active</Badge>
                  </div>
                  {exp.primary_metric_key && (
                    <p className="text-xs text-gray-500 mb-2">
                      Tracking: {exp.primary_metric_key.replace(/_/g, ' ')}
                    </p>
                  )}
                  <ProgressBar value={progress} max={100} showPercent size="sm" />
                  <div className="flex items-center justify-between mt-2 text-[10px] text-gray-400">
                    <span>
                      Started {exp.started_at ? new Date(exp.started_at).toLocaleDateString() : '--'}
                    </span>
                    <span>
                      {exp.baseline_days || 14}d baseline + {exp.intervention_days || 21}d intervention
                    </span>
                  </div>
                </Card>
              );
            })}
          </div>
        )
      )}

      {tab === 'completed' && (
        completed.length === 0 ? (
          <EmptyState
            title="No completed experiments"
            message="Completed experiments with verdicts will appear here."
          />
        ) : (
          <div className="space-y-3">
            {completed.map((exp: any) => {
              const vCfg = verdictConfig[exp.verdict] || verdictConfig.unclear;
              return (
                <Card key={exp.id}>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-semibold text-gray-900">
                      {exp.name || `Experiment #${exp.id}`}
                    </h3>
                    {exp.verdict && (
                      <Badge variant={vCfg.variant} size="sm">{vCfg.label}</Badge>
                    )}
                  </div>
                  {exp.primary_metric_key && (
                    <p className="text-xs text-gray-500 mb-1">
                      Metric: {exp.primary_metric_key.replace(/_/g, ' ')}
                    </p>
                  )}
                  <div className="flex items-center gap-4 text-[10px] text-gray-400 mt-2">
                    <span>
                      {exp.started_at ? new Date(exp.started_at).toLocaleDateString() : '--'} -
                      {exp.ended_at ? ` ${new Date(exp.ended_at).toLocaleDateString()}` : ' --'}
                    </span>
                    {exp.effect_size !== undefined && (
                      <span>Effect size: {exp.effect_size.toFixed(2)}</span>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        )
      )}

      {tab === 'design' && (
        <Card>
          <div className="text-center py-8">
            <div className="text-gray-300 mb-4">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-12 h-12 mx-auto">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M5 14.5l-.94 2.06a2.25 2.25 0 001.98 3.19h11.92a2.25 2.25 0 001.98-3.19L19 14.5M5 14.5h14" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">Design an Experiment</h3>
            <p className="text-sm text-gray-500 max-w-sm mx-auto mb-4">
              The experiment design wizard will help you set up a rigorous n-of-1 experiment
              with baseline period, intervention tracking, and pre-registered success criteria.
            </p>
            <p className="text-xs text-gray-400">Design wizard coming in next update.</p>
          </div>
        </Card>
      )}
    </div>
  );
}
