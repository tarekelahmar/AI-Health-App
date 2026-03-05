/**
 * ScoreSparkline — Compact 56px SVG sparkline for daily scores (1-10).
 *
 * Shows the last 14 days of daily scores as a polyline with gradient fill,
 * color-coded dots per score zone, and today's score + trend arrow on the right.
 *
 * Score zones:
 *   >= 7  green  (#22c55e)
 *   >= 5  amber  (#f59e0b)
 *   <  5  red    (#ef4444)
 */
import React from 'react';
import type { DailyScore } from '../../api/dailyScores';

interface ScoreSparklineProps {
  scores: DailyScore[];
  /** Total number of day slots on the X axis (default: 14) */
  days?: number;
}

const HEIGHT = 56;
const PAD_TOP = 8;
const PAD_BOTTOM = 8;
const PAD_LEFT = 4;
const RIGHT_PANEL = 48;   // space for today's score + trend on the right
const DOT_RADIUS = 3;
const Y_MIN = 1;
const Y_MAX = 10;

function scoreColor(score: number): string {
  if (score >= 7) return '#22c55e';
  if (score >= 5) return '#f59e0b';
  return '#ef4444';
}

function trendArrow(scores: DailyScore[]): { symbol: string; color: string } | null {
  if (scores.length < 2) return null;
  const last = scores[scores.length - 1].score;
  const prev = scores[scores.length - 2].score;
  const diff = last - prev;
  if (Math.abs(diff) < 0.3) return { symbol: '\u2192', color: '#9ca3af' }; // gray arrow right
  if (diff > 0) return { symbol: '\u2191', color: '#22c55e' };              // green up
  return { symbol: '\u2193', color: '#ef4444' };                             // red down
}

export function ScoreSparkline({ scores, days = 14 }: ScoreSparklineProps) {
  const chartWidth = 300;
  const plotWidth = chartWidth - PAD_LEFT - RIGHT_PANEL;
  const plotHeight = HEIGHT - PAD_TOP - PAD_BOTTOM;
  const midY = PAD_TOP + plotHeight - ((5.5 - Y_MIN) / (Y_MAX - Y_MIN)) * plotHeight;

  // Use last `days` entries
  const data = scores.slice(-days);

  // ── Empty state: visual frame with dashed midline ──
  if (data.length === 0) {
    return (
      <div className="flex items-center w-full" style={{ height: HEIGHT }}>
        <svg
          viewBox={`0 0 ${chartWidth} ${HEIGHT}`}
          preserveAspectRatio="none"
          className="w-full"
          style={{ height: HEIGHT }}
        >
          <line
            x1={PAD_LEFT} y1={midY}
            x2={chartWidth - RIGHT_PANEL} y2={midY}
            stroke="#e5e7eb"
            strokeWidth={1}
            strokeDasharray="4 3"
          />
          <text
            x={(PAD_LEFT + chartWidth - RIGHT_PANEL) / 2}
            y={HEIGHT / 2}
            textAnchor="middle"
            dominantBaseline="middle"
            fill="#d1d5db"
            fontSize="10"
          >
            No scores yet
          </text>
        </svg>
      </div>
    );
  }

  // Map data to SVG coordinates
  const xStep = data.length > 1 ? plotWidth / (data.length - 1) : 0;

  const toX = (i: number) => PAD_LEFT + i * xStep;
  const toY = (score: number) => {
    const ratio = (score - Y_MIN) / (Y_MAX - Y_MIN);
    return PAD_TOP + plotHeight - ratio * plotHeight;
  };

  // Today's score and trend
  const todayScore = data[data.length - 1];
  const trend = trendArrow(data);
  const todayColor = scoreColor(todayScore.score);

  // Unique gradient ID
  const gradId = 'spark-grad';

  // ── Single point: dot only, no line/fill ──
  if (data.length === 1) {
    const cx = PAD_LEFT + plotWidth / 2; // center the single dot
    const cy = toY(data[0].score);

    return (
      <div className="flex items-center w-full" style={{ height: HEIGHT }}>
        <svg
          viewBox={`0 0 ${chartWidth} ${HEIGHT}`}
          preserveAspectRatio="none"
          className="w-full"
          style={{ height: HEIGHT }}
        >
          <line
            x1={PAD_LEFT} y1={midY}
            x2={chartWidth - RIGHT_PANEL} y2={midY}
            stroke="#e5e7eb"
            strokeWidth={1}
            strokeDasharray="4 3"
          />
          <circle
            cx={cx}
            cy={cy}
            r={DOT_RADIUS + 1}
            fill={todayColor}
          />
          <text
            x={chartWidth - RIGHT_PANEL / 2}
            y={HEIGHT / 2 - 2}
            textAnchor="middle"
            dominantBaseline="middle"
            fill={todayColor}
            fontSize="16"
            fontWeight="700"
          >
            {todayScore.score % 1 === 0
              ? todayScore.score.toFixed(0)
              : todayScore.score.toFixed(1)}
          </text>
        </svg>
      </div>
    );
  }

  // ── 2+ points: full sparkline ──

  // Build polyline points
  const points = data.map((d, i) => `${toX(i)},${toY(d.score)}`).join(' ');

  // Build polygon for gradient fill (close at bottom)
  const firstX = toX(0);
  const lastX = toX(data.length - 1);
  const bottomY = PAD_TOP + plotHeight;
  const fillPoints = `${firstX},${bottomY} ${points} ${lastX},${bottomY}`;

  return (
    <div className="flex items-center w-full" style={{ height: HEIGHT }}>
      <svg
        viewBox={`0 0 ${chartWidth} ${HEIGHT}`}
        preserveAspectRatio="none"
        className="w-full"
        style={{ height: HEIGHT }}
      >
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={todayColor} stopOpacity={0.25} />
            <stop offset="100%" stopColor={todayColor} stopOpacity={0.02} />
          </linearGradient>
        </defs>

        {/* Gradient fill under curve */}
        <polygon points={fillPoints} fill={`url(#${gradId})`} />

        {/* Line */}
        <polyline
          points={points}
          fill="none"
          stroke={todayColor}
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity={0.7}
        />

        {/* Dots — one per data point, colored by zone */}
        {data.map((d, i) => (
          <circle
            key={d.date}
            cx={toX(i)}
            cy={toY(d.score)}
            r={i === data.length - 1 ? DOT_RADIUS + 1 : DOT_RADIUS}
            fill={scoreColor(d.score)}
            opacity={i === data.length - 1 ? 1 : 0.6}
          />
        ))}

        {/* Today's score number on the right */}
        <text
          x={chartWidth - RIGHT_PANEL / 2}
          y={HEIGHT / 2 - 2}
          textAnchor="middle"
          dominantBaseline="middle"
          fill={todayColor}
          fontSize="16"
          fontWeight="700"
        >
          {todayScore.score % 1 === 0
            ? todayScore.score.toFixed(0)
            : todayScore.score.toFixed(1)}
        </text>

        {/* Trend arrow */}
        {trend && (
          <text
            x={chartWidth - RIGHT_PANEL / 2}
            y={HEIGHT / 2 + 14}
            textAnchor="middle"
            dominantBaseline="middle"
            fill={trend.color}
            fontSize="12"
          >
            {trend.symbol}
          </text>
        )}
      </svg>
    </div>
  );
}
