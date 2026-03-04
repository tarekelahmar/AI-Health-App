import React from 'react';
import { Card } from '../ui/Card';
import type { CompanionAnalyzeResponse, Discrepancy, ContextTags } from '../../types/CompanionResponse';

interface CompanionResponseProps {
  result: CompanionAnalyzeResponse;
}

/** Severity → visual treatment */
const SEVERITY_STYLES: Record<string, { bg: string; border: string; icon: string }> = {
  info: { bg: 'bg-blue-50', border: 'border-blue-200', icon: '\u{1F4AC}' },
  notable: { bg: 'bg-amber-50', border: 'border-amber-200', icon: '\u{1F914}' },
  significant: { bg: 'bg-orange-50', border: 'border-orange-300', icon: '\u26A0\uFE0F' },
};

/** Format a context tag value for display */
function formatTag(key: string, value: unknown): string | null {
  if (value === null || value === undefined || value === false) return null;
  if (value === true) return key.replace(/_/g, ' ');
  if (typeof value === 'string') return value;
  return null;
}

export function CompanionResponse({ result }: CompanionResponseProps) {
  const { companion_response, discrepancies, context_tags, extraction_method } = result;

  // Nothing to show if LLM was disabled and no discrepancies
  if (extraction_method === 'deterministic_only' && discrepancies.length === 0) {
    return null;
  }

  const hasCompanionText = companion_response && companion_response.text;
  const hasDiscrepancies = discrepancies.length > 0;
  const hasTags = context_tags && Object.values(context_tags).some((v) => v !== null);

  // If LLM was disabled, show a simple fallback
  if (extraction_method === 'deterministic_only') {
    return (
      <Card className="mt-3">
        <div className="text-center py-2">
          <p className="text-xs text-gray-400">Check-in saved. AI companion is disabled.</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-3 mt-3">
      {/* Companion response text */}
      {hasCompanionText && (
        <Card className="border-l-4 border-l-primary-400">
          <p className="text-sm text-gray-700 leading-relaxed">
            {companion_response!.text}
          </p>
          {companion_response!.pattern_referenced && (
            <div className="mt-2 flex items-center gap-1">
              <span className="text-[10px] text-primary-500 bg-primary-50 px-1.5 py-0.5 rounded">
                Pattern referenced
              </span>
            </div>
          )}
        </Card>
      )}

      {/* Discrepancy callouts */}
      {hasDiscrepancies && (
        <div className="space-y-2">
          {discrepancies.map((d: Discrepancy, i: number) => {
            const style = SEVERITY_STYLES[d.severity] || SEVERITY_STYLES.info;
            return (
              <div
                key={i}
                className={`${style.bg} border ${style.border} rounded-lg p-3`}
              >
                <div className="flex items-start gap-2">
                  <span className="text-sm flex-shrink-0">{style.icon}</span>
                  <p className="text-xs text-gray-700 leading-relaxed">
                    {d.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Context tags (non-editable pills) */}
      {hasTags && (
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(context_tags as ContextTags).map(([key, value]) => {
            const label = formatTag(key, value);
            if (!label) return null;
            return (
              <span
                key={key}
                className="text-[10px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full"
              >
                {label}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}
