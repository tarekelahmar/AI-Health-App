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
}

const FIELDS: SliderField[] = [
  { key: 'energy', label: 'Energy', emoji: '\u26a1', lowLabel: 'Exhausted', highLabel: 'Energized' },
  { key: 'mood', label: 'Mood', emoji: '\ud83d\ude0a', lowLabel: 'Low', highLabel: 'Great' },
  { key: 'stress', label: 'Stress', emoji: '\ud83d\ude13', lowLabel: 'Calm', highLabel: 'Overwhelmed' },
  { key: 'focus', label: 'Focus', emoji: '\ud83c\udfaf', lowLabel: 'Scattered', highLabel: 'Sharp' },
  { key: 'sleep_quality', label: 'Sleep Quality', emoji: '\ud83d\udca4', lowLabel: 'Terrible', highLabel: 'Amazing' },
];

interface JournalFormProps {
  existingCheckIn: CheckIn | null;
  onSave: (data: {
    energy: number;
    mood: number;
    stress: number;
    focus: number;
    sleep_quality: number;
    notes: string;
    behaviors_json: Record<string, any>;
  }) => Promise<void>;
  saving: boolean;
}

export function JournalForm({ existingCheckIn, onSave, saving }: JournalFormProps) {
  const [values, setValues] = useState<Record<string, number>>({
    energy: 5,
    mood: 5,
    stress: 5,
    focus: 5,
    sleep_quality: 5,
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
      const updated: Record<string, number> = {};
      for (const f of FIELDS) {
        const val = (existingCheckIn as any)[f.key];
        updated[f.key] = val != null ? val : 5;
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
      energy: values.energy,
      mood: values.mood,
      stress: values.stress,
      focus: values.focus,
      sleep_quality: values.sleep_quality,
      notes,
      behaviors_json: factors,
    });
    setHasEdited(false);
  };

  const isExisting = existingCheckIn && existingCheckIn.energy != null;

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

        {/* 3. Score sliders */}
        <div className="space-y-3">
          {FIELDS.map((field) => (
            <div key={field.key}>
              <div className="flex items-center justify-between mb-0.5">
                <label className="text-sm text-gray-600">
                  {field.emoji} {field.label}
                </label>
                <span className="text-sm font-medium text-gray-800 min-w-[2ch] text-right">
                  {values[field.key]}
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={10}
                step={1}
                value={values[field.key]}
                onChange={(e) => handleSliderChange(field.key, parseInt(e.target.value, 10))}
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
