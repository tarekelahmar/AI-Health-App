import React, { useState } from 'react';
import { KNOWN_FACTORS, FACTOR_CATEGORIES } from '../../types/JournalFactors';
import type { ExtractedFactor } from '../../types/JournalFactors';

interface FactorTagsProps {
  factors: Record<string, any>;
  onChange: (factors: Record<string, any>) => void;
  extracting?: boolean;
  llmAvailable?: boolean;
}

export function FactorTags({ factors, onChange, extracting, llmAvailable }: FactorTagsProps) {
  const [showPicker, setShowPicker] = useState(false);

  const toggleFactor = (key: string) => {
    const updated = { ...factors };
    if (updated[key] === true) {
      delete updated[key];
    } else {
      updated[key] = true;
    }
    onChange(updated);
  };

  const removeFactor = (key: string) => {
    const updated = { ...factors };
    delete updated[key];
    onChange(updated);
  };

  // Separate active factors into known and custom
  const activeFactors = Object.entries(factors).filter(([_, v]) => v === true);
  const hasFactors = activeFactors.length > 0;

  if (extracting) {
    return (
      <div className="py-3">
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <div className="w-4 h-4 border-2 border-gray-300 border-t-primary-500 rounded-full animate-spin" />
          Extracting factors from your journal...
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
          Today's Factors
        </span>
        <button
          type="button"
          onClick={() => setShowPicker(!showPicker)}
          className="text-xs text-primary-600 hover:text-primary-700"
        >
          {showPicker ? 'Done' : '+ Add'}
        </button>
      </div>

      {/* Active factor pills */}
      {hasFactors && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {activeFactors.map(([key]) => {
            const meta = KNOWN_FACTORS[key];
            const label = meta ? meta.label : key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            const icon = meta?.icon || '🏷️';
            return (
              <button
                key={key}
                type="button"
                onClick={() => removeFactor(key)}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-red-50 hover:text-red-600 hover:border-red-200 transition-colors"
                title="Click to remove"
              >
                <span>{icon}</span>
                {label}
                <span className="ml-0.5 opacity-60">x</span>
              </button>
            );
          })}
        </div>
      )}

      {!hasFactors && !showPicker && (
        <p className="text-xs text-gray-400 mb-2">
          {llmAvailable
            ? 'Write about your day and factors will be extracted automatically.'
            : 'Tap "+ Add" to tag what you did today.'}
        </p>
      )}

      {/* Manual factor picker grid */}
      {showPicker && (
        <div className="bg-gray-50 rounded-lg p-3 space-y-3">
          {FACTOR_CATEGORIES.map((cat) => {
            const catFactors = Object.entries(KNOWN_FACTORS).filter(
              ([_, m]) => m.category === cat.key
            );
            if (catFactors.length === 0) return null;
            return (
              <div key={cat.key}>
                <div className="text-[10px] font-medium text-gray-400 uppercase mb-1.5">
                  {cat.label}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {catFactors.map(([key, meta]) => {
                    const isActive = factors[key] === true;
                    return (
                      <button
                        key={key}
                        type="button"
                        onClick={() => toggleFactor(key)}
                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
                          isActive
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : 'bg-white text-gray-500 border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <span>{meta.icon}</span>
                        {meta.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
