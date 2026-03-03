import React from 'react';

const dotColors = {
  good: 'bg-emerald-500',
  caution: 'bg-amber-500',
  alert: 'bg-red-500',
  neutral: 'bg-gray-400',
  inactive: 'bg-gray-300',
  info: 'bg-cyan-500',
};

interface StatusDotProps {
  status: keyof typeof dotColors;
  label: string;
  size?: 'sm' | 'md';
  pulse?: boolean;
}

export function StatusDot({ status, label, size = 'sm', pulse = false }: StatusDotProps) {
  const dotSize = size === 'sm' ? 'h-2 w-2' : 'h-3 w-3';
  const textSize = size === 'sm' ? 'text-xs' : 'text-sm';

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="relative flex">
        {pulse && (
          <span
            className={`animate-ping absolute inline-flex h-full w-full rounded-full ${dotColors[status]} opacity-75`}
          />
        )}
        <span className={`relative inline-flex rounded-full ${dotSize} ${dotColors[status]}`} />
      </span>
      <span className={`${textSize} text-gray-600`}>{label}</span>
    </span>
  );
}
