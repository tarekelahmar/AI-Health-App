import React from 'react';
import { Card } from '../ui/Card';
import type { WellnessScore } from '../../types/WellnessScore';

interface WellnessTimelineProps {
  scores: WellnessScore[];
  selectedDate: string | null;
  onDateSelect: (date: string) => void;
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'bg-emerald-500 text-white';
  if (score >= 60) return 'bg-amber-500 text-white';
  if (score >= 40) return 'bg-orange-500 text-white';
  return 'bg-red-500 text-white';
}

function formatDay(dateStr: string): string {
  const d = new Date(dateStr + 'T12:00:00');
  return d.toLocaleDateString('en-US', { weekday: 'short' });
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T12:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function WellnessTimeline({ scores, selectedDate, onDateSelect }: WellnessTimelineProps) {
  // Show last 7 days of scores
  const recent = scores.slice(0, 7).reverse();

  if (recent.length === 0) {
    return null;
  }

  return (
    <Card>
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Last 7 Days</h3>
      <div className="flex items-end justify-between gap-1">
        {recent.map((ws) => {
          const isSelected = ws.score_date === selectedDate;
          return (
            <button
              key={ws.score_date}
              onClick={() => onDateSelect(ws.score_date)}
              className={`flex flex-col items-center flex-1 min-w-0 p-1 rounded-lg transition-colors ${
                isSelected ? 'bg-gray-100' : 'hover:bg-gray-50'
              }`}
            >
              <span className="text-[10px] text-gray-400 mb-1">{formatDay(ws.score_date)}</span>
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold ${getScoreColor(ws.score)} ${
                  isSelected ? 'ring-2 ring-primary-500 ring-offset-1' : ''
                }`}
              >
                {Math.round(ws.score)}
              </div>
              <span className="text-[10px] text-gray-400 mt-1">{formatDate(ws.score_date)}</span>
            </button>
          );
        })}
      </div>

      {/* 30-day trend (simple sparkline via CSS) */}
      {scores.length > 7 && (
        <div className="mt-4 pt-3 border-t border-gray-100">
          <h4 className="text-xs text-gray-500 mb-2">30-Day Trend</h4>
          <div className="flex items-end gap-px h-12">
            {scores
              .slice(0, 30)
              .reverse()
              .map((ws, i) => {
                const height = Math.max(4, (ws.score / 100) * 48);
                const color =
                  ws.score >= 80 ? 'bg-emerald-400' :
                  ws.score >= 60 ? 'bg-amber-400' :
                  ws.score >= 40 ? 'bg-orange-400' :
                  'bg-red-400';
                return (
                  <div
                    key={ws.score_date}
                    className={`flex-1 rounded-t ${color} transition-all`}
                    style={{ height: `${height}px` }}
                    title={`${ws.score_date}: ${Math.round(ws.score)}`}
                  />
                );
              })}
          </div>
        </div>
      )}
    </Card>
  );
}
