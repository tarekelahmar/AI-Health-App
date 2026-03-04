/**
 * Journal V3 — Weekly Domain Check-in Card.
 *
 * Appears inline in the chat when a domain check-in is due (>7 days since last).
 * Shows 5 sliders for life domains (1.0-10.0, step 0.5).
 * After confirmation: collapses to a compact summary with color-coded pills.
 *
 * Same inline card pattern as DailyScoreCard.
 */
import React, { useState } from 'react';

interface WeeklyDomainCardProps {
  /** Whether the check-in has already been confirmed */
  confirmed: boolean;
  /** Called when user submits the domain ratings */
  onConfirm: (scores: Record<string, number>) => void;
  /** Whether confirmation is in progress */
  confirming?: boolean;
}

const DOMAINS = [
  { key: 'career', label: 'Career & Work', emoji: '💼', low: 'Struggling', high: 'Thriving' },
  { key: 'relationship', label: 'Relationship', emoji: '❤️', low: 'Distant', high: 'Connected' },
  { key: 'social', label: 'Family & Social', emoji: '👥', low: 'Isolated', high: 'Supported' },
  { key: 'health', label: 'Health', emoji: '💪', low: 'Poor', high: 'Strong' },
  { key: 'finance', label: 'Finance', emoji: '💰', low: 'Stressed', high: 'Secure' },
] as const;

const DEFAULT_SCORE = 5.0;

function scoreColor(value: number): string {
  if (value >= 7) return '#10b981';
  if (value >= 5) return '#f59e0b';
  return '#ef4444';
}

export function WeeklyDomainCard({
  confirmed,
  onConfirm,
  confirming = false,
}: WeeklyDomainCardProps) {
  const [scores, setScores] = useState<Record<string, number>>(
    Object.fromEntries(DOMAINS.map(d => [d.key, DEFAULT_SCORE]))
  );

  const updateScore = (key: string, value: number) => {
    setScores(prev => ({ ...prev, [key]: value }));
  };

  // ── Confirmed state: compact pills ──
  if (confirmed) {
    return (
      <div className="flex justify-start mb-3">
        <div className="bg-gray-50 border border-gray-200 rounded-2xl rounded-bl-md px-4 py-2.5 inline-flex items-center gap-3 flex-wrap">
          <span className="text-xs text-gray-400">Domains</span>
          {DOMAINS.map(d => (
            <span
              key={d.key}
              className="inline-flex items-center gap-1 text-xs font-medium"
            >
              <span>{d.emoji}</span>
              <span style={{ color: scoreColor(scores[d.key]) }}>
                {scores[d.key]}
              </span>
            </span>
          ))}
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#10b981"
            strokeWidth="3"
            strokeLinecap="round"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
      </div>
    );
  }

  // ── Interactive state: 5 sliders + submit ──
  return (
    <div className="flex justify-start mb-3">
      <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md p-4 w-full max-w-[85%] shadow-sm">
        <div className="mb-3">
          <span className="text-sm font-medium text-gray-700">Weekly Life Domain Check-in</span>
          <p className="text-xs text-gray-400 mt-0.5">
            How are these areas of your life feeling this week?
          </p>
        </div>

        <div className="space-y-3">
          {DOMAINS.map(d => {
            const val = scores[d.key];
            const col = scoreColor(val);
            const pct = ((val - 1) / 9) * 100;

            return (
              <div key={d.key}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-gray-500">
                    {d.emoji} {d.label}
                  </span>
                  <span className="text-sm font-bold" style={{ color: col }}>
                    {val}
                  </span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="10"
                  step="0.5"
                  value={val}
                  onChange={(e) => updateScore(d.key, parseFloat(e.target.value))}
                  className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
                  style={{
                    background: `linear-gradient(to right, ${col} ${pct}%, #e5e7eb ${pct}%)`,
                  }}
                />
                <div className="flex justify-between text-[10px] text-gray-300 mt-0.5">
                  <span>{d.low}</span>
                  <span>{d.high}</span>
                </div>
              </div>
            );
          })}
        </div>

        <button
          onClick={() => onConfirm(scores)}
          disabled={confirming}
          className="w-full mt-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded-xl transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          {confirming ? 'Saving...' : 'Submit weekly check-in'}
        </button>
      </div>
    </div>
  );
}
