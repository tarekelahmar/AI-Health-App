/**
 * Journal V3 — History Sub-tab (inside Insights).
 *
 * Shows wellness timeline, weekly synthesis, session list, and export button.
 */
import React from 'react';
import { WellnessTimeline } from './WellnessTimeline';
import { SynthesisCard } from './SynthesisCard';
import type { WellnessScore } from '../../types/WellnessScore';
import type { MilestoneData, PhaseData } from '../../api/milestones';
import type { SessionGroup } from '../../types/JournalChat';

interface HistoryTabProps {
  scoreHistory: WellnessScore[];
  selectedDate: string;
  onDateSelect: (date: string) => void;
  milestones: MilestoneData[];
  phases: PhaseData[];
  weeklySynthesis: Record<string, any> | null;
  sessionGroups: SessionGroup[];
  onExport: () => void;
}

function scoreColor(score: number | null): string {
  if (score === null) return 'text-gray-400';
  if (score >= 7) return 'text-green-600';
  if (score >= 5) return 'text-amber-500';
  return 'text-red-500';
}

export function HistoryTab({
  scoreHistory,
  selectedDate,
  onDateSelect,
  milestones,
  phases,
  weeklySynthesis,
  sessionGroups,
  onExport,
}: HistoryTabProps) {
  return (
    <div className="space-y-4">
      {/* Timeline */}
      {scoreHistory.length > 0 && (
        <WellnessTimeline
          scores={scoreHistory}
          selectedDate={selectedDate}
          onDateSelect={onDateSelect}
          milestones={milestones}
          phases={phases}
        />
      )}

      {/* Weekly synthesis */}
      {weeklySynthesis && Object.keys(weeklySynthesis).length > 0 && (
        <SynthesisCard synthesis={weeklySynthesis} type="weekly" />
      )}

      {/* Session list */}
      {sessionGroups.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-3">
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Recent Sessions
          </h4>
          <div className="space-y-1.5">
            {sessionGroups.slice().reverse().slice(0, 20).map((g) => {
              const d = new Date(g.started_at);
              const dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
              const preview = g.messages.find(m => m.role === 'user')?.content ?? '';

              return (
                <div
                  key={g.session_id}
                  className="flex items-center gap-3 py-1.5 border-b border-gray-50 last:border-0"
                >
                  <span className="text-xs text-gray-400 w-14 shrink-0">{dateStr}</span>
                  <span className={`text-xs font-bold w-8 shrink-0 ${scoreColor(g.daily_score)}`}>
                    {g.daily_score ?? '—'}
                  </span>
                  <span className="text-xs text-gray-500 truncate flex-1">
                    {preview.length > 60 ? preview.slice(0, 60) + '...' : preview || 'No messages'}
                  </span>
                  <span className="text-[10px] text-gray-300 shrink-0">
                    {g.messages.length} msg{g.messages.length !== 1 ? 's' : ''}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Export */}
      <div className="text-center pt-2">
        <button
          onClick={onExport}
          className="text-xs text-gray-400 hover:text-gray-600 underline"
        >
          Export journal data
        </button>
      </div>
    </div>
  );
}
