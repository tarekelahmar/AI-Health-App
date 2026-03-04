/**
 * Journal V3 — Actions Sub-tab (inside Insights).
 *
 * Shows pattern-derived action suggestions and today's tracked behavioral factors.
 * Replaces the ActionsStub from Phase 2.
 */
import React from 'react';
import type { JournalPatternData } from '../../types/JournalFactors';
import { KNOWN_FACTORS } from '../../types/JournalFactors';

// ── Types ────────────────────────────────────────────────────────

interface ActionsTabProps {
  patterns: JournalPatternData[];
  todayFactors: Record<string, any> | null;
}

interface ActionSuggestion {
  icon: string;
  text: string;
  patternType: string;
  /** 'done' | 'not_yet' | 'watch' */
  status: 'done' | 'not_yet' | 'watch';
  inputFactors: string[];
}

// ── Pattern → Action Transformation ──────────────────────────────

function formatFactorLabel(factor: string): string {
  return factor.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function getActionStatus(
  patternType: string,
  inputFactors: string[],
  todayFactors: Record<string, any> | null,
): 'done' | 'not_yet' | 'watch' {
  if (!todayFactors) return 'not_yet';

  if (patternType === 'crash') {
    // For crash patterns: "watch" if the crash combo is active, "done" if avoided
    const crashActive = inputFactors.every((f) => {
      const val = todayFactors[f];
      // Negative factors (isolated, alcohol) being true = crash risk
      // Positive factors (exercised, social_contact) being false = crash risk
      if (['isolated', 'alcohol', 'caffeine_late', 'late_screen'].includes(f)) {
        return val === true;
      }
      return val === false;
    });
    return crashActive ? 'watch' : 'done';
  }

  // For floor/formula/boost: check if positive factors are done
  const allDone = inputFactors.every((f) => todayFactors[f] === true);
  return allDone ? 'done' : 'not_yet';
}

function patternToAction(
  pattern: JournalPatternData,
  todayFactors: Record<string, any> | null,
): ActionSuggestion | null {
  // Only confirmed patterns are actionable
  if (pattern.status !== 'confirmed') return null;

  const labels = pattern.input_factors.map(formatFactorLabel);
  const status = getActionStatus(pattern.pattern_type, pattern.input_factors, todayFactors);
  const metric = pattern.output_metric.replace(/_/g, ' ');

  switch (pattern.pattern_type) {
    case 'floor':
      return {
        icon: '🛡️',
        text: `${labels[0]} is your floor — keep it up`,
        patternType: 'floor',
        status,
        inputFactors: pattern.input_factors,
      };
    case 'formula':
      return {
        icon: '✨',
        text: `Hit your formula: ${labels.join(' + ')}`,
        patternType: 'formula',
        status,
        inputFactors: pattern.input_factors,
      };
    case 'crash':
      return {
        icon: '📉',
        text: `Watch out: ${labels.join(' + ')} leads to crashes`,
        patternType: 'crash',
        status,
        inputFactors: pattern.input_factors,
      };
    case 'boost':
      return {
        icon: '🚀',
        text: `Try ${labels[0]} for a ${metric} boost`,
        patternType: 'boost',
        status,
        inputFactors: pattern.input_factors,
      };
    default:
      return null;
  }
}

// ── Status Indicators ────────────────────────────────────────────

function StatusBadge({ status }: { status: 'done' | 'not_yet' | 'watch' }) {
  if (status === 'done') {
    return (
      <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-green-100 text-green-700">
        ✓ Done
      </span>
    );
  }
  if (status === 'watch') {
    return (
      <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">
        ⚠ Watch
      </span>
    );
  }
  return (
    <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
      ○ Not yet
    </span>
  );
}

// ── Factor Category Grouping ─────────────────────────────────────

const CATEGORY_ORDER = ['physical', 'social', 'routine', 'wellness', 'sleep', 'substance', 'supplement'];
const CATEGORY_LABELS: Record<string, string> = {
  physical: 'Physical',
  social: 'Social',
  routine: 'Routine',
  wellness: 'Wellness',
  sleep: 'Sleep',
  substance: 'Substance',
  supplement: 'Supplement',
};

function groupFactorsByCategory(
  factors: Record<string, any>,
): Record<string, { key: string; value: any; label: string; icon: string }[]> {
  const groups: Record<string, { key: string; value: any; label: string; icon: string }[]> = {};

  for (const [key, value] of Object.entries(factors)) {
    if (typeof value !== 'boolean') continue;
    const meta = KNOWN_FACTORS[key];
    const category = meta?.category ?? 'other';
    if (!groups[category]) groups[category] = [];
    groups[category].push({
      key,
      value,
      label: meta?.label ?? formatFactorLabel(key),
      icon: meta?.icon ?? '•',
    });
  }

  return groups;
}

// ── Main Component ───────────────────────────────────────────────

export function ActionsTab({ patterns, todayFactors }: ActionsTabProps) {
  // Build action suggestions from confirmed patterns
  const actions = patterns
    .map((p) => patternToAction(p, todayFactors))
    .filter((a): a is ActionSuggestion => a !== null);

  // Deduplicate by text (same pattern can appear for multiple metrics)
  const seen = new Set<string>();
  const uniqueActions = actions.filter((a) => {
    const key = `${a.patternType}:${a.inputFactors.join(',')}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  const hasFactors = todayFactors && Object.keys(todayFactors).some(
    (k) => typeof todayFactors[k] === 'boolean',
  );
  const factorGroups = todayFactors ? groupFactorsByCategory(todayFactors) : {};

  // Empty state: no patterns AND no factors
  if (uniqueActions.length === 0 && !hasFactors) {
    return (
      <div className="border-2 border-dashed border-gray-200 rounded-xl p-8 text-center">
        <div className="text-3xl mb-3">{'🎯'}</div>
        <h3 className="text-sm font-semibold text-gray-700 mb-1">
          Building Your Actions
        </h3>
        <p className="text-xs text-gray-400 max-w-xs mx-auto leading-relaxed">
          Actions appear once the system detects confirmed patterns in your journal data.
          Keep journaling with behavioral tags — the system needs at least 7 tagged entries
          to start detecting patterns.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Suggested Actions */}
      {uniqueActions.length > 0 && (
        <div>
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
            Today's Actions
          </h3>
          <div className="bg-white border border-gray-200 rounded-xl divide-y divide-gray-50">
            {uniqueActions.map((action, i) => (
              <div
                key={`${action.patternType}-${i}`}
                className="flex items-center gap-3 px-4 py-3"
              >
                <span className="text-base shrink-0">{action.icon}</span>
                <span className="text-sm text-gray-700 flex-1">{action.text}</span>
                <StatusBadge status={action.status} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Today's Factor Log */}
      {hasFactors && (
        <div>
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
            Today's Factors
          </h3>
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <div className="space-y-3">
              {CATEGORY_ORDER.map((cat) => {
                const items = factorGroups[cat];
                if (!items || items.length === 0) return null;
                return (
                  <div key={cat}>
                    <span className="text-[10px] font-medium text-gray-400 uppercase tracking-wide">
                      {CATEGORY_LABELS[cat] ?? cat}
                    </span>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {items.map((f) => (
                        <span
                          key={f.key}
                          className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full border ${
                            f.value
                              ? 'bg-green-50 border-green-200 text-green-700'
                              : 'bg-gray-50 border-gray-200 text-gray-400'
                          }`}
                        >
                          <span>{f.icon}</span>
                          <span>{f.label}</span>
                          <span className="text-[10px]">{f.value ? '✓' : '✗'}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* No factors yet hint (when actions exist but no factors) */}
      {uniqueActions.length > 0 && !hasFactors && (
        <div className="text-center py-4">
          <p className="text-xs text-gray-400">
            No factors tracked today yet. Keep journaling — factors are extracted from your conversations.
          </p>
        </div>
      )}
    </div>
  );
}
