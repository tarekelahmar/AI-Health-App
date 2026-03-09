/**
 * ScoreSparkline — Compact SVG sparkline for daily scores (1-10).
 *
 * Always renders a structured chart frame with three soft zone tinting bands.
 * Data (dots, line, fill) layers on top as scores accumulate.
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

const HEIGHT_DATA = 64;
const HEIGHT_EMPTY = 80;
const PAD_TOP = 12;
const PAD_BOTTOM = 12;
const PAD_LEFT = 4;
const RIGHT_PANEL = 48; // space for today's score + trend on the right
const DOT_RADIUS = 3;
const Y_MIN = 1;
const Y_MAX = 10;

const CHART_WIDTH = 300;

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
  if (Math.abs(diff) < 0.3) return { symbol: '\u2192', color: '#9ca3af' };
  if (diff > 0) return { symbol: '\u2191', color: '#22c55e' };
  return { symbol: '\u2193', color: '#ef4444' };
}

/** Shared chart frame: three soft zone tinting bands */
function ChartFrame({
  plotLeft,
  plotRight,
  toY,
}: {
  plotLeft: number;
  plotRight: number;
  toY: (score: number) => number;
}) {
  const y10 = toY(10);
  const y7 = toY(7);
  const y5 = toY(5);
  const y1 = toY(1);

  return (
    <>
      <rect x={plotLeft} y={y10} width={plotRight - plotLeft} height={y7 - y10}
        fill="#22c55e" opacity={0.03} />
      <rect x={plotLeft} y={y7} width={plotRight - plotLeft} height={y5 - y7}
        fill="#f59e0b" opacity={0.03} />
      <rect x={plotLeft} y={y5} width={plotRight - plotLeft} height={y1 - y5}
        fill="#ef4444" opacity={0.03} />
    </>
  );
}

export function ScoreSparkline({ scores, days = 14 }: ScoreSparklineProps) {
  const data = scores.slice(-days);
  const isEmpty = data.length === 0;
  const height = isEmpty ? HEIGHT_EMPTY : HEIGHT_DATA;
  const plotWidth = CHART_WIDTH - PAD_LEFT - RIGHT_PANEL;
  const plotHeight = height - PAD_TOP - PAD_BOTTOM;

  const toY = (score: number) => {
    const ratio = (score - Y_MIN) / (Y_MAX - Y_MIN);
    return PAD_TOP + plotHeight - ratio * plotHeight;
  };

  const plotLeft = PAD_LEFT;
  const plotRight = CHART_WIDTH - RIGHT_PANEL;

  // ── Empty state ──
  if (isEmpty) {
    return (
      <div className="flex items-center w-full" style={{ height }}>
        <svg
          viewBox={`0 0 ${CHART_WIDTH} ${height}`}
          preserveAspectRatio="none"
          className="w-full"
          style={{ height }}
        >
          <ChartFrame plotLeft={plotLeft} plotRight={plotRight} toY={toY} />
          <text
            x={(plotLeft + plotRight) / 2}
            y={height / 2}
            textAnchor="middle"
            dominantBaseline="middle"
            fill="#d1d5db"
            fontSize="10"
          >
            Your trend will appear here
          </text>
        </svg>
      </div>
    );
  }

  // Map data to SVG coordinates
  const xStep = data.length > 1 ? plotWidth / (data.length - 1) : 0;
  const toX = (i: number) => PAD_LEFT + i * xStep;

  const todayScore = data[data.length - 1];
  const trend = trendArrow(data);
  const todayColor = scoreColor(todayScore.score);
  const gradId = 'spark-grad';

  // ── Single point: dot only, no line/fill ──
  if (data.length === 1) {
    const cx = PAD_LEFT + plotWidth / 2;
    const cy = toY(data[0].score);

    return (
      <div className="flex items-center w-full" style={{ height }}>
        <svg
          viewBox={`0 0 ${CHART_WIDTH} ${height}`}
          preserveAspectRatio="none"
          className="w-full"
          style={{ height }}
        >
          <ChartFrame plotLeft={plotLeft} plotRight={plotRight} toY={toY} />
          <circle cx={cx} cy={cy} r={DOT_RADIUS + 1} fill={todayColor} />
          <text
            x={CHART_WIDTH - RIGHT_PANEL / 2}
            y={height / 2 - 2}
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

  const points = data.map((d, i) => `${toX(i)},${toY(d.score)}`).join(' ');
  const firstX = toX(0);
  const lastX = toX(data.length - 1);
  const bottomY = PAD_TOP + plotHeight;
  const fillPoints = `${firstX},${bottomY} ${points} ${lastX},${bottomY}`;

  return (
    <div className="flex items-center w-full" style={{ height }}>
      <svg
        viewBox={`0 0 ${CHART_WIDTH} ${height}`}
        preserveAspectRatio="none"
        className="w-full"
        style={{ height }}
      >
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={todayColor} stopOpacity={0.25} />
            <stop offset="100%" stopColor={todayColor} stopOpacity={0.02} />
          </linearGradient>
        </defs>

        {/* Chart frame: zone bands */}
        <ChartFrame plotLeft={plotLeft} plotRight={plotRight} toY={toY} />

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
          x={CHART_WIDTH - RIGHT_PANEL / 2}
          y={height / 2 - 2}
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
            x={CHART_WIDTH - RIGHT_PANEL / 2}
            y={height / 2 + 14}
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
