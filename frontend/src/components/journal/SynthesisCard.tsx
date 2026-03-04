import React from 'react';
import { Card } from '../ui/Card';

interface SynthesisCardProps {
  synthesis: Record<string, any>;
  type: 'weekly' | 'monthly';
}

const PHASE_COLORS: Record<string, string> = {
  CRISIS: 'bg-red-100 text-red-700',
  STABILIZING: 'bg-amber-100 text-amber-700',
  BUILDING: 'bg-blue-100 text-blue-700',
  STABLE: 'bg-emerald-100 text-emerald-700',
  GROWING: 'bg-purple-100 text-purple-700',
};

export function SynthesisCard({ synthesis, type }: SynthesisCardProps) {
  if (!synthesis || Object.keys(synthesis).length === 0) return null;

  if (type === 'weekly') return <WeeklySynthesisCard data={synthesis} />;
  return <MonthlySynthesisCard data={synthesis} />;
}

function WeeklySynthesisCard({ data }: { data: Record<string, any> }) {
  const phase = data.phase;
  const trend = data.trend;

  return (
    <Card>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-gray-700">Weekly Summary</h3>
        {phase && (
          <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${PHASE_COLORS[phase.phase] || 'bg-gray-100 text-gray-600'}`}>
            {phase.phase}
          </span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3 mb-3">
        {data.avg_wellbeing != null && (
          <div className="text-center">
            <div className="text-xs text-gray-400">Wellbeing</div>
            <div className="text-sm font-semibold text-gray-700">{data.avg_wellbeing}</div>
          </div>
        )}
        {data.avg_energy != null && (
          <div className="text-center">
            <div className="text-xs text-gray-400">Energy</div>
            <div className="text-sm font-semibold text-gray-700">{data.avg_energy}</div>
          </div>
        )}
        {data.avg_mood != null && (
          <div className="text-center">
            <div className="text-xs text-gray-400">Mood</div>
            <div className="text-sm font-semibold text-gray-700">{data.avg_mood}</div>
          </div>
        )}
      </div>

      {data.entry_count != null && (
        <p className="text-xs text-gray-400 mb-2">
          {data.entry_count} entries | Trend: {trend === 'up' ? '\u2191 Up' : trend === 'down' ? '\u2193 Down' : '\u2192 Stable'}
        </p>
      )}

      {/* Domain changes */}
      {data.domain_changes && Object.keys(data.domain_changes).length > 0 && (
        <div className="mb-2">
          <div className="text-[10px] text-gray-400 mb-1">Domain shifts:</div>
          <div className="flex flex-wrap gap-1">
            {Object.entries(data.domain_changes).map(([domain, delta]) => (
              <span
                key={domain}
                className={`text-[10px] px-1.5 py-0.5 rounded ${
                  (delta as number) > 0 ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'
                }`}
              >
                {domain} {(delta as number) > 0 ? '+' : ''}{delta as number}
              </span>
            ))}
          </div>
        </div>
      )}

      {data.companion_question && (
        <div className="mt-3 pt-2 border-t border-gray-100">
          <p className="text-xs text-gray-600 italic">{data.companion_question}</p>
        </div>
      )}
    </Card>
  );
}

function MonthlySynthesisCard({ data }: { data: Record<string, any> }) {
  return (
    <Card>
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Monthly Review</h3>

      {data.phase_narrative && (
        <p className="text-xs text-gray-600 mb-3">{data.phase_narrative}</p>
      )}

      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="text-center">
          <div className="text-xs text-gray-400">Entries</div>
          <div className="text-sm font-semibold text-gray-700">{data.entry_count}</div>
        </div>
        {data.avg_wellbeing != null && (
          <div className="text-center">
            <div className="text-xs text-gray-400">Avg Wellbeing</div>
            <div className="text-sm font-semibold text-gray-700">{data.avg_wellbeing}</div>
          </div>
        )}
      </div>

      {data.milestones && data.milestones.length > 0 && (
        <div className="mb-3">
          <div className="text-[10px] text-gray-400 mb-1">Milestones:</div>
          {data.milestones.map((m: string, i: number) => (
            <div key={i} className="text-xs text-gray-600 flex items-center gap-1 mb-0.5">
              <span className="text-amber-500">{'\u2B50'}</span> {m}
            </div>
          ))}
        </div>
      )}

      {data.focus_areas && data.focus_areas.length > 0 && (
        <div className="mt-2 pt-2 border-t border-gray-100">
          <div className="text-[10px] text-gray-400 mb-1">Focus areas:</div>
          {data.focus_areas.map((area: string, i: number) => (
            <div key={i} className="text-xs text-gray-600">{'\u2022'} {area}</div>
          ))}
        </div>
      )}
    </Card>
  );
}
