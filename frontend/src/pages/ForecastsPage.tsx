import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Card } from '../components/ui/Card';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Badge } from '../components/ui/Badge';
import { FanChart } from '../components/forecasts/FanChart';
import { fetchForecast } from '../api/forecasts';
import type { ForecastResponse } from '../types/Forecast';

const METRIC_OPTIONS = [
  { key: 'hrv_rmssd_ms', label: 'HRV', color: '#0d9488' },
  { key: 'sleep_duration_minutes', label: 'Sleep', color: '#6366f1' },
  { key: 'resting_heart_rate_bpm', label: 'RHR', color: '#ef4444' },
  { key: 'sleep_efficiency_pct', label: 'Sleep Eff.', color: '#8b5cf6' },
  { key: 'subjective_energy', label: 'Energy', color: '#f59e0b' },
  { key: 'respiratory_rate_brpm', label: 'Resp Rate', color: '#f97316' },
];

export default function ForecastsPage() {
  const navigate = useNavigate();
  const { userId } = useAuth();
  const [selectedMetric, setSelectedMetric] = useState(METRIC_OPTIONS[0]);
  const [loading, setLoading] = useState(true);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);

  useEffect(() => {
    if (!userId) {
      navigate('/login');
      return;
    }
    loadForecast(selectedMetric.key);
  }, [userId, selectedMetric.key]);

  const loadForecast = async (metricKey: string) => {
    setLoading(true);
    try {
      const data = await fetchForecast(metricKey, 7);
      setForecast(data);
    } catch (error) {
      console.error('Failed to load forecast', error);
      setForecast(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Forecasts</h1>
        <p className="text-sm text-gray-500 mt-0.5">7-day predictions with confidence intervals</p>
      </div>

      {/* Metric selector pills */}
      <div className="flex flex-wrap gap-2">
        {METRIC_OPTIONS.map((opt) => (
          <button
            key={opt.key}
            onClick={() => setSelectedMetric(opt)}
            className={`px-3 py-1.5 text-xs font-medium rounded-full transition-colors ${
              selectedMetric.key === opt.key
                ? 'bg-primary-100 text-primary-700 ring-1 ring-primary-300'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Fan chart */}
      {loading ? (
        <LoadingSpinner label="Loading forecast..." size="sm" />
      ) : forecast && forecast.predictions.length > 0 ? (
        <>
          <FanChart
            historical={forecast.historical}
            predictions={forecast.predictions}
            metricLabel={selectedMetric.label}
            color={selectedMetric.color}
          />

          {/* Forecast detail table */}
          <Card>
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Prediction Details</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-100">
                    <th className="text-left py-2 pr-3 font-medium">Date</th>
                    <th className="text-right py-2 px-2 font-medium">Predicted</th>
                    <th className="text-right py-2 px-2 font-medium">80% CI</th>
                    <th className="text-right py-2 pl-2 font-medium">95% CI</th>
                  </tr>
                </thead>
                <tbody>
                  {forecast.predictions.map((p) => (
                    <tr key={p.date} className="border-b border-gray-50 last:border-0">
                      <td className="py-1.5 pr-3 text-gray-700">
                        {new Date(p.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                      </td>
                      <td className="py-1.5 px-2 text-right font-medium text-gray-900">
                        {p.predicted}
                      </td>
                      <td className="py-1.5 px-2 text-right text-gray-500">
                        {p.ci_80_low} - {p.ci_80_high}
                      </td>
                      <td className="py-1.5 pl-2 text-right text-gray-400">
                        {p.ci_95_low} - {p.ci_95_high}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Metadata */}
          {forecast.metadata && (
            <div className="flex items-center gap-3 text-[10px] text-gray-400">
              <span>Method: {forecast.metadata.method}</span>
              <span>Training: {forecast.metadata.training_points} points</span>
              <span>Horizon: {forecast.metadata.horizon} days</span>
            </div>
          )}
        </>
      ) : (
        <Card>
          <div className="text-center py-8">
            <p className="text-sm text-gray-500">
              {forecast?.message || 'Not enough data to generate a forecast for this metric.'}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              At least 14 data points are needed for reliable predictions.
            </p>
          </div>
        </Card>
      )}
    </div>
  );
}
