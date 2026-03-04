import React, { useState } from 'react';
import { Card } from '../ui/Card';

interface JournalOnboardingProps {
  onComplete: (depthLevel: number) => void;
}

const DEPTH_LEVELS = [
  {
    level: 1,
    title: 'Check-in',
    emoji: '\u2705',
    description: 'Quick daily score. Minimal text.',
    detail: 'Best for: building the habit first. Short companion responses, basic visualisations.',
  },
  {
    level: 2,
    title: 'Reflective',
    emoji: '\uD83D\uDCDD',
    description: 'Scores + short reflection. Pattern tracking.',
    detail: 'Best for: most users. Follow-up questions, radar chart, pattern observations.',
  },
  {
    level: 3,
    title: 'Deep Analysis',
    emoji: '\uD83D\uDD2C',
    description: 'Detailed writing. Psychological pattern analysis.',
    detail: 'Best for: experienced journalers. The companion challenges you and names uncomfortable patterns.',
  },
];

const CALIBRATION = [
  { score: '9-10', meaning: 'Peak day. Everything clicked.', color: 'text-emerald-600' },
  { score: '7-8', meaning: 'Good day. Solid and functional.', color: 'text-emerald-500' },
  { score: '5-6', meaning: 'Okay. Getting by.', color: 'text-amber-500' },
  { score: '3-4', meaning: 'Struggling. Low energy or mood.', color: 'text-orange-500' },
  { score: '1-2', meaning: 'Crisis. Can\'t function normally.', color: 'text-red-500' },
];

export function JournalOnboarding({ onComplete }: JournalOnboardingProps) {
  const [step, setStep] = useState(0);
  const [selectedDepth, setSelectedDepth] = useState(2);

  return (
    <div className="space-y-4">
      <div className="text-center">
        <h1 className="text-lg font-bold text-gray-900">Welcome to Your Journal</h1>
        <p className="text-xs text-gray-500 mt-1">
          {step === 0 ? 'Choose your journaling style' : 'How to calibrate your scores'}
        </p>
      </div>

      {step === 0 && (
        <>
          <div className="space-y-3">
            {DEPTH_LEVELS.map((d) => (
              <button
                key={d.level}
                onClick={() => setSelectedDepth(d.level)}
                className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
                  selectedDepth === d.level
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{d.emoji}</span>
                  <div>
                    <div className="font-semibold text-gray-800 text-sm">{d.title}</div>
                    <div className="text-xs text-gray-500">{d.description}</div>
                  </div>
                </div>
                {selectedDepth === d.level && (
                  <p className="text-xs text-gray-400 mt-2 ml-10">{d.detail}</p>
                )}
              </button>
            ))}
          </div>
          <button
            onClick={() => setStep(1)}
            className="w-full py-3 bg-primary-600 text-white rounded-xl font-medium text-sm hover:bg-primary-700 transition-colors"
          >
            Continue
          </button>
        </>
      )}

      {step === 1 && (
        <>
          <Card>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">
              What does a score mean?
            </h3>
            <p className="text-xs text-gray-400 mb-3">
              Your scores are personal. What matters is consistency, not absolute numbers.
              Here's a rough guide:
            </p>
            <div className="space-y-2">
              {CALIBRATION.map((c) => (
                <div key={c.score} className="flex items-center gap-3">
                  <span className={`text-sm font-mono font-bold w-10 ${c.color}`}>{c.score}</span>
                  <span className="text-xs text-gray-600">{c.meaning}</span>
                </div>
              ))}
            </div>
          </Card>
          <button
            onClick={() => onComplete(selectedDepth)}
            className="w-full py-3 bg-primary-600 text-white rounded-xl font-medium text-sm hover:bg-primary-700 transition-colors"
          >
            Start Journaling
          </button>
          <button
            onClick={() => setStep(0)}
            className="w-full py-2 text-xs text-gray-400 hover:text-gray-600"
          >
            Back
          </button>
        </>
      )}
    </div>
  );
}
