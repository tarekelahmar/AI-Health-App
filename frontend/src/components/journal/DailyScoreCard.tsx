/**
 * Journal V3 — Daily Score Card.
 *
 * Appears inline in the chat when the companion proposes a score.
 * Shows a single slider (1.0-10.0, step 0.5), color-coded.
 * After confirmation: collapses to a compact pill ("Today: 7.0 ✓").
 *
 * Based on reference-chat-ui.jsx DailyScoreCard pattern.
 */
import React, { useState } from 'react';

interface DailyScoreCardProps {
  /** Score proposed by the companion (parsed from text) */
  proposedScore: number;
  /** Whether the score has already been confirmed */
  confirmed: boolean;
  /** Called when user confirms the score */
  onConfirm: (score: number) => void;
  /** Whether confirmation is in progress */
  confirming?: boolean;
}

function scoreColor(value: number): string {
  if (value >= 7) return '#10b981';
  if (value >= 5) return '#f59e0b';
  return '#ef4444';
}

export function DailyScoreCard({
  proposedScore,
  confirmed,
  onConfirm,
  confirming = false,
}: DailyScoreCardProps) {
  const [value, setValue] = useState(proposedScore);
  const col = scoreColor(value);

  // ── Confirmed state: compact pill ──
  if (confirmed) {
    return (
      <div className="flex justify-start mb-3">
        <div className="bg-gray-50 border border-gray-200 rounded-2xl rounded-bl-md px-4 py-2.5 inline-flex items-center gap-2">
          <span className="text-xs text-gray-400">Today</span>
          <span className="text-base font-bold" style={{ color: col }}>
            {value}
          </span>
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

  // ── Interactive state: slider + confirm ──
  const pct = ((value - 1) / 9) * 100;

  return (
    <div className="flex justify-start mb-3">
      <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md p-4 w-full max-w-[85%] shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs text-gray-400">How does today feel overall?</span>
          <span className="text-xl font-bold" style={{ color: col }}>
            {value}
          </span>
        </div>

        <input
          type="range"
          min="1"
          max="10"
          step="0.5"
          value={value}
          onChange={(e) => setValue(parseFloat(e.target.value))}
          className="w-full h-2 rounded-full appearance-none cursor-pointer mb-3"
          style={{
            background: `linear-gradient(to right, ${col} ${pct}%, #e5e7eb ${pct}%)`,
          }}
        />

        <div className="flex justify-between text-xs text-gray-400 mb-3">
          <span>Struggling</span>
          <span>Thriving</span>
        </div>

        <button
          onClick={() => onConfirm(value)}
          disabled={confirming}
          className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded-xl transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          {confirming
            ? 'Saving...'
            : value === proposedScore
              ? 'Looks right'
              : `Confirm ${value}`}
        </button>
      </div>
    </div>
  );
}
