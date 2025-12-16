/**
 * ALPHA WIRING: Page 4 - Insights Feed (Core Page)
 * This is the home screen
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { fetchInsightsFeed } from '../api/insights';
import { Insight } from '../types/Insight';
import { whoopStatus } from '../api/providers';
import { fetchMetricSeries } from '../api/metrics';
import apiClient from '../api/client';

type SilenceState = 
  | 'no_provider'
  | 'no_recent_data'
  | 'baseline_building'
  | 'no_signal'
  | null;

export default function InsightsFeedPage() {
  const navigate = useNavigate();
  const { userId } = useAuth();
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningLoop, setRunningLoop] = useState(false);
  const [silenceState, setSilenceState] = useState<SilenceState>(null);
  const [showWhyExplanation, setShowWhyExplanation] = useState(false);

  useEffect(() => {
    if (!userId) {
      navigate('/login');
      return;
    }

    loadInsights();
  }, [userId, navigate]);

  const determineSilenceState = async (userId: number): Promise<SilenceState> => {
    // Check if provider is connected
    try {
      const providerStatus = await whoopStatus(userId);
      if (!providerStatus.connected) {
        return 'no_provider';
      }
    } catch (error) {
      // If we can't check status, assume no provider
      return 'no_provider';
    }

    // Check if we have recent data and baseline status
    try {
      // Try to fetch a common metric to check data availability
      const metricResponse = await fetchMetricSeries(userId, 'recovery_score');
      const { points, baseline } = metricResponse;

      // Check if we have recent data (within last 7 days)
      const sevenDaysAgo = new Date();
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
      const recentPoints = points.filter(p => new Date(p.timestamp) >= sevenDaysAgo);

      if (recentPoints.length === 0) {
        return 'no_recent_data';
      }

      // Check baseline status
      if (!baseline.available) {
        return 'baseline_building';
      }

      // If we have baseline but no insights, it means no meaningful signal
      // IMPORTANT: Only return 'no_signal' if we successfully fetched data and baseline
      return 'no_signal';
    } catch (error) {
      // If we can't fetch metrics, be conservative: assume no recent data
      // This prevents API failures from incorrectly showing "no signal"
      // We don't know the state, so we default to the more conservative assumption
      console.warn('Could not determine data state, defaulting to no_recent_data:', error);
      return 'no_recent_data';
    }
  };

  const loadInsights = async () => {
    if (!userId) return;

    setLoading(true);
    try {
      const response = await fetchInsightsFeed(userId);
      setInsights(response.items || []);
      
      // If no insights, determine why
      if (response.items.length === 0) {
        const state = await determineSilenceState(userId);
        setSilenceState(state);
      } else {
        setSilenceState(null);
      }
    } catch (error) {
      console.error('Failed to load insights', error);
      setInsights([]);
      // Try to determine silence state even on error
      if (userId) {
        const state = await determineSilenceState(userId).catch(() => 'no_provider');
        setSilenceState(state);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRunLoop = async () => {
    if (!userId) return;

    setRunningLoop(true);
    try {
      // ALPHA: Manual loop trigger
      await apiClient.post('/insights/run', null, {
        params: { user_id: userId },
      });
      // Reload insights after running
      setTimeout(() => {
        loadInsights();
      }, 2000);
    } catch (error) {
      console.error('Failed to run loop', error);
      alert('Failed to run analysis. Please try again.');
    } finally {
      setRunningLoop(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto p-4 space-y-4">
        {/* Header */}
        <div className="bg-white rounded-lg p-4 flex items-center justify-between">
          <h1 className="text-xl font-semibold text-gray-900">Insights</h1>
          <div className="flex gap-2">
            {/* ALPHA: Hidden admin button for manual loop */}
            <button
              onClick={handleRunLoop}
              disabled={runningLoop}
              className="text-xs text-gray-500 hover:text-gray-700 px-2 py-1 border rounded"
              title="Run daily loop (alpha)"
            >
              {runningLoop ? 'Running...' : 'Run Loop'}
            </button>
            <button
              onClick={() => navigate('/narratives')}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              Narratives
            </button>
          </div>
        </div>

        {/* Insights Feed */}
        {insights.length === 0 ? (
          <SilenceStateMessage 
            state={silenceState} 
            showWhyExplanation={showWhyExplanation}
            onToggleWhy={() => setShowWhyExplanation(!showWhyExplanation)}
          />
        ) : (
          <div className="space-y-3">
            {insights.map((insight) => (
              <div key={insight.id} className="bg-white rounded-lg p-4 border">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-medium text-gray-900">{insight.title}</h3>
                  <span className="text-xs px-2 py-1 bg-gray-100 rounded text-gray-600">
                    {insight.status}
                  </span>
                </div>
                <p className="text-sm text-gray-700 mb-2">{insight.summary}</p>
                
                {/* Confidence / Uncertainty */}
                {insight.confidence !== undefined && (
                  <div className="mb-2">
                    <div className="flex items-center gap-2 text-xs text-gray-600">
                      <span>Confidence: {Math.round(insight.confidence * 100)}%</span>
                      {insight.uncertainty && (
                        <span className="text-gray-500">• {insight.uncertainty}</span>
                      )}
                    </div>
                  </div>
                )}

                {/* Why? expandable section */}
                {insight.evidence && (
                  <details className="mt-2">
                    <summary className="text-sm text-blue-600 cursor-pointer hover:text-blue-700">
                      Why?
                    </summary>
                    <div className="mt-2 p-2 bg-gray-50 rounded text-xs text-gray-600">
                      <pre className="whitespace-pre-wrap">
                        {JSON.stringify(insight.evidence, null, 2)}
                      </pre>
                    </div>
                  </details>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Silence State Message Component
 * Renders appropriate messaging for each of the 4 silence states
 */
function SilenceStateMessage({ 
  state, 
  showWhyExplanation, 
  onToggleWhy 
}: { 
  state: SilenceState; 
  showWhyExplanation: boolean;
  onToggleWhy: () => void;
}) {
  const getStateContent = () => {
    switch (state) {
      case 'no_provider':
        return {
          title: 'No wearable connected yet',
          message: 'Connect a wearable device to begin tracking your health patterns over time.',
          trustLine: 'The system waits for data before generating insights, ensuring accuracy and relevance.',
          icon: '📱'
        };
      
      case 'no_recent_data':
        return {
          title: 'Waiting for recent data',
          message: 'Your device is connected, but we need recent measurements to identify patterns.',
          trustLine: 'The system only analyzes data it can trust, which requires consistent recent measurements.',
          icon: '⏳'
        };
      
      case 'baseline_building':
        return {
          title: 'Baseline still forming',
          message: 'We\'re learning your normal patterns. This takes time to ensure insights are meaningful.',
          trustLine: 'The system builds a personalized baseline before detecting changes, preventing false signals.',
          icon: '📊'
        };
      
      case 'no_signal':
        return {
          title: 'Nothing stands out yet',
          message: 'Your data shows normal variation. The system only surfaces insights when patterns are clear and meaningful.',
          trustLine: 'Silence here means the system is confident there\'s nothing unusual to report—this is intentional restraint.',
          icon: '✓'
        };
      
      default:
        return {
          title: 'No insights available',
          message: 'The system is analyzing your data. Insights will appear when meaningful patterns are detected.',
          trustLine: 'The system prioritizes accuracy over volume, only sharing insights it can support with confidence.',
          icon: '🔍'
        };
    }
  };

  const content = getStateContent();

  return (
    <div className="bg-white rounded-lg p-8">
      <div className="text-center space-y-4">
        <div className="text-4xl mb-2">{content.icon}</div>
        <h2 className="text-xl font-semibold text-gray-900">{content.title}</h2>
        <p className="text-gray-600 max-w-md mx-auto">{content.message}</p>
        
        {/* Trust-reinforcing line */}
        <div className="pt-4 border-t border-gray-200">
          <p className="text-sm text-gray-500 italic max-w-md mx-auto">
            {content.trustLine}
          </p>
        </div>

        {/* Expandable "Why don't I see insights?" section */}
        <div className="pt-4">
          <button
            onClick={onToggleWhy}
            className="text-sm text-blue-600 hover:text-blue-700 underline"
          >
            {showWhyExplanation ? 'Hide explanation' : 'Why don\'t I see insights?'}
          </button>
          
          {showWhyExplanation && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg text-left max-w-md mx-auto">
              <p className="text-sm text-gray-700 mb-2">
                <strong>Why the system stays quiet:</strong>
              </p>
              <ul className="text-sm text-gray-600 space-y-2 list-disc list-inside">
                <li>Missing or insufficient data prevents reliable analysis</li>
                <li>Baselines need time to establish your personal patterns</li>
                <li>Normal variation doesn't warrant insights—silence is intentional</li>
                <li>The system only speaks when it has high confidence in what it observes</li>
              </ul>
              <p className="text-sm text-gray-500 mt-3 italic">
                This restraint is a feature, not a bug. It ensures insights are trustworthy and meaningful.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

