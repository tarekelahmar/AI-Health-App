import React from 'react';
import type { RegimeType } from '../../types/Regime';

interface RegimeBannerProps {
  regime: RegimeType;
  context: string;
}

const regimeStyles: Record<string, { bg: string; border: string; icon: string; label: string }> = {
  illness: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    icon: '!',
    label: 'Illness Detected',
  },
  high_stress: {
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    icon: '!',
    label: 'High Stress',
  },
  travel: {
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    icon: '~',
    label: 'Travel Disruption',
  },
  recovery: {
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    icon: '+',
    label: 'Recovery Phase',
  },
  training_peak: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    icon: '^',
    label: 'Training Peak',
  },
  menstrual_phase: {
    bg: 'bg-pink-50',
    border: 'border-pink-200',
    icon: '~',
    label: 'Cycle Phase',
  },
};

export function RegimeBanner({ regime, context }: RegimeBannerProps) {
  if (regime === 'normal') return null;

  const style = regimeStyles[regime] || regimeStyles.high_stress;

  return (
    <div className={`${style.bg} ${style.border} border rounded-xl p-4 mb-4`}>
      <div className="flex items-start gap-3">
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
          regime === 'illness' ? 'bg-red-200 text-red-800' :
          regime === 'recovery' ? 'bg-emerald-200 text-emerald-800' :
          'bg-amber-200 text-amber-800'
        }`}>
          {style.icon}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-900">{style.label}</p>
          <p className="text-xs text-gray-600 mt-0.5 leading-relaxed">{context}</p>
        </div>
      </div>
    </div>
  );
}
