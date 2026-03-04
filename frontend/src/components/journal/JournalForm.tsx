import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card } from '../ui/Card';
import { FactorTags } from './FactorTags';
import { extractFactors } from '../../api/journalPatterns';
import type { CheckIn } from '../../types/CheckIn';

interface SliderField {
  key: string;
  label: string;
  emoji: string;
  lowLabel: string;
  highLabel: string;
  /** Calibration hint shown on hover (optional, only for overall_wellbeing) */
  calibrationHint?: string;
}

const FIELDS: SliderField[] = [
  {
    key: 'overall_wellbeing',
    label: 'Overall Wellbeing',
    emoji: '\u{1F31F}',
    lowLabel: 'Crisis',
    highLabel: 'Thriving',
    calibrationHint: '10 = Thriving | 7 = Good day | 5 = Neutral | 3 = Struggling | 1 = Crisis',
  },
  { key: 'energy', label: 'Energy', emoji: '\u26a1', lowLabel: 'Exhausted', highLabel: 'Energized' },
  { key: 'mood', label: 'Mood', emoji: '\ud83d\ude0a', lowLabel: 'Low', highLabel: 'Great' },
  { key: 'focus', label: 'Focus', emoji: '\ud83c\udfaf', lowLabel: 'Scattered', highLabel: 'Sharp' },
  { key: 'connection', label: 'Connection', emoji: '\ud83e\udd1d', lowLabel: 'Isolated', highLabel: 'Connected' },
];

const DEFAULT_VALUE = 5.0;
const SLIDER_MIN = 1.0;
const SLIDER_MAX = 10.0;
const SLIDER_STEP = 0.5;

interface JournalFormProps {
  existingCheckIn: CheckIn | null;
  onSave: (data: {
    overall_wellbeing: number;
    energy: number;
    mood: number;
    focus: number;
    connection: number;
    notes: string;
    behaviors_json: Record<string, any>;
  }) => Promise<void>;
  saving: boolean;
}

function formatSliderValue(val: number): string {
  return val % 1 === 0 ? val.toString() : val.toFixed(1);
}

export function JournalForm({ existingCheckIn, onSave, saving }: JournalFormProps) {
  const [values, setValues] = useState<Record<string, number>>({
    overall_wellbeing: DEFAULT_VALUE,
    energy: DEFAULT_VALUE,
    mood: DEFAULT_VALUE,
    focus: DEFAULT_VALUE,
    connection: DEFAULT_VALUE,
  });
  const [notes, setNotes] = useState('');
  const [factors, setFactors] = useState<Record<string, any>>({});
  const [hasEdited, setHasEdited] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [llmAvailable, setLlmAvailable] = useState(false);
  const extractTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastExtractedTextRef = useRef('');

  useEffect(() => {
    if (existingCheckIn) {
      // Detect V2 entry (has overall_wellbeing) vs V1 entry
      const isV2 = existingCheckIn.overall_wellbeing != null;

      const updated: Record<string, number> = {};
      for (const f of FIELDS) {
        const val = (existingCheckIn as any)[f.key];
        updated[f.key] = val != null ? val : DEFAULT_VALUE;
      }

      // If loading a V1 entry, map old fields to reasonable V2 defaults
      if (!isV2 && existingCheckIn.energy != null) {
        // V1 was 0-10 int; V2 is 1.0-10.0. Approximate mapping:
        // v2 = max(1, v1)  (since V1 0 maps to V2 1.0 minimum)
        updated.overall_wellbeing = DEFAULT_VALUE; // No V1 equivalent
        updated.energy = Math.max(SLIDER_MIN, existingCheckIn.energy ?? DEFAULT_VALUE);
        updated.mood = Math.max(SLIDER_MIN, existingCheckIn.mood ?? DEFAULT_VALUE);
        updated.focus = Math.max(SLIDER_MIN, existingCheckIn.focus ?? DEFAULT_VALUE);
        updated.connection = DEFAULT_VALUE; // No V1 equivalent
      }

      setValues(updated);
      setNotes(existingCheckIn.notes || '');
      if (existingCheckIn.behaviors_json && Object.keys(existingCheckIn.behaviors_json).length > 0) {
        setFactors(existingCheckIn.behaviors_json);
      }
    }
  }, [existingCheckIn]);

  const runExtraction = useCallback(async (text: string) => {
    if (!text.trim() || text.trim().length < 20) return;
    if (text.trim() === lastExtractedTextRef.current) return;

    setExtracting(true);
    try {
      const result = await extractFactors(text);
      lastExtractedTextRef.current = text.trim();
      setLlmAvailable(result.extraction_method === 'llm');

      const allFactors = [...result.factors, ...result.custom_factors];
      if (allFactors.length > 0) {
        // Merge AI-extracted with manually set factors (manual takes precedence)
        const newFactors = { ...factors };
        for (const f of allFactors) {
          if (!(f.key in newFactors)) {
            newFactors[f.key] = f.value;
          }
        }
        setFactors(newFactors);
        setHasEdited(true);
      }
    } catch (err) {
      console.error('Factor extraction failed:', err);
    } finally {
      setExtracting(false);
    }
  }, [factors]);

  const handleNotesChange = (text: string) => {
    setNotes(text);
    setHasEdited(true);

    // Debounce extraction: run 1.5s after user stops typing
    if (extractTimeoutRef.current) {
      clearTimeout(extractTimeoutRef.current);
    }
    extractTimeoutRef.current = setTimeout(() => {
      runExtraction(text);
    }, 1500);
  };

  const handleSliderChange = (key: string, val: number) => {
    setValues((prev) => ({ ...prev, [key]: val }));
    setHasEdited(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSave({
      overall_wellbeing: values.overall_wellbeing,
      energy: values.energy,
      mood: values.mood,
      focus: values.focus,
      connection: values.connection,
      notes,
      behaviors_json: factors,
    });
    setHasEdited(false);
  };

  // Detect existing entry (V2 has overall_wellbeing, V1 has energy)
  const isExisting = existingCheckIn && (
    existingCheckIn.overall_wellbeing != null || existingCheckIn.energy != null
  );

  return (
    <Card>
      <form onSubmit={handleSubmit}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-700">Daily Check-in</h3>
          {isExisting && !hasEdited && (
            <span className="text-xs text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">Logged</span>
          )}
        </div>

        {/* 1. Journal text area (primary input) */}
        <div className="mb-4">
          <label className="text-xs font-medium text-gray-500 block mb-1.5">
            How was your day?
          </label>
          <textarea
            value={notes}
            onChange={(e) => handleNotesChange(e.target.value)}
            placeholder="Went for a run this morning, had lunch with friends, feeling good about work..."
            className="w-full border border-gray-200 rounded-lg p-3 text-sm text-gray-700 resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            rows={4}
          />
        </div>

        {/* 2. Factor tags (AI-extracted or manual) */}
        <div className="mb-4">
          <FactorTags
            factors={factors}
            onChange={(newFactors) => { setFactors(newFactors); setHasEdited(true); }}
            extracting={extracting}
            llmAvailable={llmAvailable}
          />
        </div>

        {/* 3. Score sliders (V2: 1.0-10.0, step 0.5) */}
        <div className="space-y-3">
          {FIELDS.map((field) => (
            <div key={field.key}>
              <div className="flex items-center justify-between mb-0.5">
                <label className="text-sm text-gray-600" title={field.calibrationHint}>
                  {field.emoji} {field.label}
                  {field.calibrationHint && (
                    <span className="ml-1 text-gray-300 cursor-help" title={field.calibrationHint}>
                      ?
                    </span>
                  )}
                </label>
                <span className="text-sm font-medium text-gray-800 min-w-[3ch] text-right">
                  {formatSliderValue(values[field.key])}
                </span>
              </div>
              <input
                type="range"
                min={SLIDER_MIN}
                max={SLIDER_MAX}
                step={SLIDER_STEP}
                value={values[field.key]}
                onChange={(e) => handleSliderChange(field.key, parseFloat(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
              />
              <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                <span>{field.lowLabel}</span>
                <span>{field.highLabel}</span>
              </div>
            </div>
          ))}
        </div>

        <button
          type="submit"
          disabled={saving}
          className="mt-4 w-full py-2.5 px-4 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? 'Saving...' : isExisting ? 'Update Check-in' : 'Save Check-in'}
        </button>
      </form>
    </Card>
  );
}
