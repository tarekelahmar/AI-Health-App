import React, { useState, useEffect } from 'react';
import { PatternCard } from './PatternCard';
import { getJournalPatterns } from '../../api/journalPatterns';
import type { JournalPatternData } from '../../types/JournalFactors';

export function JournalInsights() {
  const [patterns, setPatterns] = useState<JournalPatternData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPatterns();
  }, []);

  const loadPatterns = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getJournalPatterns();
      // Sort: confirmed first, then by confidence desc
      data.sort((a, b) => {
        if (a.status === 'confirmed' && b.status !== 'confirmed') return -1;
        if (b.status === 'confirmed' && a.status !== 'confirmed') return 1;
        return b.confidence - a.confidence;
      });
      setPatterns(data);
    } catch (err) {
      console.error('Failed to load patterns:', err);
      setError('Failed to load insights');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white rounded-xl border border-gray-100 p-4 animate-pulse">
            <div className="h-4 bg-gray-100 rounded w-1/2 mb-3" />
            <div className="h-3 bg-gray-50 rounded w-3/4 mb-2" />
            <div className="h-2 bg-gray-50 rounded w-full mb-1" />
            <div className="h-2 bg-gray-50 rounded w-full" />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-red-500">{error}</p>
        <button
          onClick={loadPatterns}
          className="mt-2 text-xs text-primary-600 hover:text-primary-700"
        >
          Try again
        </button>
      </div>
    );
  }

  if (patterns.length === 0) {
    return (
      <div className="text-center py-10">
        <div className="text-3xl mb-3">🔍</div>
        <h3 className="text-sm font-semibold text-gray-700 mb-1">
          Building Your Insights
        </h3>
        <p className="text-xs text-gray-400 max-w-xs mx-auto leading-relaxed">
          Keep journaling with behavioral tags to discover patterns in your data.
          The system needs at least 7 tagged entries to start detecting patterns.
        </p>
        <div className="mt-4 w-48 mx-auto">
          <div className="flex items-center justify-between text-[10px] text-gray-400 mb-1">
            <span>Progress</span>
            <span>Need 7+ entries</span>
          </div>
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div className="h-full bg-primary-400 rounded-full" style={{ width: '0%' }} />
          </div>
        </div>
      </div>
    );
  }

  const confirmed = patterns.filter((p) => p.status === 'confirmed');
  const hypotheses = patterns.filter((p) => p.status === 'hypothesis');

  return (
    <div className="space-y-4">
      {confirmed.length > 0 && (
        <div>
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
            Confirmed Patterns ({confirmed.length})
          </h3>
          <div className="space-y-3">
            {confirmed.map((p, i) => (
              <PatternCard key={`confirmed-${i}`} pattern={p} />
            ))}
          </div>
        </div>
      )}

      {hypotheses.length > 0 && (
        <div>
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
            Emerging Patterns ({hypotheses.length})
          </h3>
          <div className="space-y-3">
            {hypotheses.map((p, i) => (
              <PatternCard key={`hypothesis-${i}`} pattern={p} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
