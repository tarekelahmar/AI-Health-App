import React from 'react';

const variantColors = {
  default: 'bg-primary-500',
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  danger: 'bg-red-500',
};

interface ProgressBarProps {
  value: number;
  max: number;
  label?: string;
  showPercent?: boolean;
  variant?: keyof typeof variantColors;
  size?: 'sm' | 'md';
}

export function ProgressBar({
  value,
  max,
  label,
  showPercent = false,
  variant = 'default',
  size = 'sm',
}: ProgressBarProps) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  const barHeight = size === 'sm' ? 'h-1.5' : 'h-2.5';

  return (
    <div className="w-full">
      {(label || showPercent) && (
        <div className="flex justify-between items-center mb-1">
          {label && <span className="text-xs text-gray-600">{label}</span>}
          {showPercent && <span className="text-xs font-medium text-gray-700">{pct}%</span>}
        </div>
      )}
      <div className={`w-full bg-gray-200 rounded-full ${barHeight}`} role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div
          className={`${variantColors[variant]} ${barHeight} rounded-full transition-all duration-300`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
