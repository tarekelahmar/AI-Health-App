import React from 'react';

interface WellnessScoreRingProps {
  score: number | null;
  size?: number;
  yesterdayScore?: number | null;
}

function getScoreColor(score: number): string {
  if (score >= 80) return '#10b981'; // emerald-500
  if (score >= 60) return '#f59e0b'; // amber-500
  if (score >= 40) return '#f97316'; // orange-500
  return '#ef4444'; // red-500
}

function getScoreLabel(score: number): string {
  if (score >= 85) return 'Excellent';
  if (score >= 70) return 'Good';
  if (score >= 55) return 'Fair';
  if (score >= 40) return 'Low';
  return 'Poor';
}

export function WellnessScoreRing({ score, size = 160, yesterdayScore }: WellnessScoreRingProps) {
  const strokeWidth = size * 0.08;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const center = size / 2;

  if (score === null || score === undefined) {
    return (
      <div className="flex flex-col items-center">
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth={strokeWidth}
          />
          <text
            x={center}
            y={center}
            textAnchor="middle"
            dominantBaseline="central"
            className="fill-gray-400"
            fontSize={size * 0.12}
          >
            No data
          </text>
        </svg>
      </div>
    );
  }

  const progress = score / 100;
  const dashOffset = circumference * (1 - progress);
  const color = getScoreColor(score);
  const label = getScoreLabel(score);

  const trend = yesterdayScore != null ? score - yesterdayScore : null;

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Background circle */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="#f3f4f6"
          strokeWidth={strokeWidth}
        />
        {/* Progress arc */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          transform={`rotate(-90 ${center} ${center})`}
          style={{ transition: 'stroke-dashoffset 0.6s ease' }}
        />
        {/* Score number */}
        <text
          x={center}
          y={center - size * 0.06}
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={size * 0.28}
          fontWeight="700"
          fill={color}
        >
          {Math.round(score)}
        </text>
        {/* Label */}
        <text
          x={center}
          y={center + size * 0.14}
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={size * 0.09}
          className="fill-gray-500"
        >
          {label}
        </text>
      </svg>
      {/* Trend indicator */}
      {trend !== null && (
        <div className={`flex items-center gap-1 text-sm mt-1 ${trend >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
          <span>{trend >= 0 ? '\u2191' : '\u2193'}</span>
          <span>{Math.abs(Math.round(trend))} vs yesterday</span>
        </div>
      )}
    </div>
  );
}
