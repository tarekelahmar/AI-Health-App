/**
 * Journal V3 — Factors Sub-tab (inside Insights).
 *
 * Shows pattern cards (confirmed + hypothesis) and the correlation chart.
 */
import React from 'react';
import { JournalInsights } from './JournalInsights';
import { CorrelationChart } from './CorrelationChart';
import type { JournalPatternData } from '../../types/JournalFactors';

interface FactorsTabProps {
  patterns: JournalPatternData[];
}

export function FactorsTab({ patterns }: FactorsTabProps) {
  return (
    <div className="space-y-4">
      <JournalInsights />
      {patterns.length > 0 && <CorrelationChart patterns={patterns} />}
    </div>
  );
}
