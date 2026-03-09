/**
 * HabitDetail -- Habit-type action detail screen.
 *
 * Shows impact, consistency, before/after chart, AI interpretation,
 * confounding factors, and consistency calendar for an ongoing habit.
 *
 * Design ref: journalling-wireframes-v2.jsx -> HabitDetailScreen
 */
import React from 'react';

// -- Journal Design Tokens ------------------------------------------------
const JT = {
  bg: '#FAF8F5',
  surface: '#F3F0EB',
  card: '#FFFFFF',
  border: '#E8E3DC',
  text: '#2A2520',
  textSecondary: '#8C8278',
  textMuted: '#B5ADA4',
  accent: '#C4704B',
  secondary: '#B8A48C',
  secondaryLight: '#EDE6DC',
  positive: '#7A8F6B',
  positiveLight: '#E8EDE4',
  negative: '#C47A6B',
  negativeLight: '#F5E6E2',
};

// -- Types ----------------------------------------------------------------

interface ScoreDataPoint {
  date: string;
  score: number;
}

export interface HabitDetailProps {
  /** Habit display title */
  title: string;
  /** e.g. "Health" */
  category: string;
  /** Start date ISO string (YYYY-MM-DD) */
  startDate: string;
  /** Average score lift on active days */
  scoreLift: number;
  /** Average score on active days */
  avgActive: number;
  /** Average score on inactive days */
  avgInactive: number;
  /** Days the habit was completed */
  completedDays: number;
  /** Total eligible days since start */
  totalDays: number;
  /** Daily score data points for the before/after chart */
  scoreData: ScoreDataPoint[];
  /** AI interpretation text */
  interpretation: string;
  /** Other factors active in the same period */
  confoundingFactors: string[];
  /** Dates (ISO strings) when the habit was completed */
  completedDates: string[];
  /** Override today's date for testing (ISO string, defaults to real today) */
  today?: string;
  /** Back navigation callback */
  onBack?: () => void;
}

// -- Helpers --------------------------------------------------------------

function formatSinceDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  const date = new Date(y, m - 1, d);
  return date.toLocaleDateString('en-GB', { month: 'short', day: 'numeric' });
}

/** Build a sequential list of days for the current month (no week structure). */
function getMonthDays(today: string): { date: string; isFuture: boolean; isToday: boolean }[] {
  const [y, m] = today.split('-').map(Number);
  const daysInMonth = new Date(y, m, 0).getDate(); // m is already 1-indexed here

  const days: { date: string; isFuture: boolean; isToday: boolean }[] = [];
  for (let day = 1; day <= daysInMonth; day++) {
    const iso = `${y}-${String(m).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    days.push({ date: iso, isFuture: iso > today, isToday: iso === today });
  }
  return days;
}

// -- Before / After SVG Chart ---------------------------------------------

function BeforeAfterChart({
  scoreData,
  startDate,
}: {
  scoreData: ScoreDataPoint[];
  startDate: string;
}) {
  if (scoreData.length < 2) return null;

  const sorted = [...scoreData].sort((a, b) => a.date.localeCompare(b.date));
  const startIdx = sorted.findIndex((d) => d.date >= startDate);
  const dividerIdx = startIdx >= 0 ? startIdx : Math.floor(sorted.length / 3);

  const W = 300;
  const H = 85;
  const xStep = W / (sorted.length - 1 || 1);
  const dividerX = dividerIdx * xStep;

  // Map score (0-10) to y pixel
  const yOf = (score: number) => H - (score / 10) * H;

  // Polyline points -- NO dots (FIX 2)
  const points = sorted.map((d, i) => `${i * xStep},${yOf(d.score)}`).join(' ');

  // Averages
  const beforeSlice = sorted.slice(0, dividerIdx);
  const afterSlice = sorted.slice(dividerIdx);
  const avg = (arr: ScoreDataPoint[]) =>
    arr.length > 0 ? arr.reduce((s, d) => s + d.score, 0) / arr.length : 0;
  const beforeAvg = avg(beforeSlice);
  const afterAvg = avg(afterSlice);

  return (
    <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet">
      {/* FIX 2: Zone fills -- before = rose/pink, after = green */}
      <rect x="0" y="0" width={dividerX} height={H} fill={JT.negativeLight} />
      <rect x={dividerX} y="0" width={W - dividerX} height={H} fill={JT.positiveLight} />

      {/* Dashed average lines */}
      <line
        x1="0"
        y1={yOf(beforeAvg)}
        x2={dividerX}
        y2={yOf(beforeAvg)}
        stroke={JT.negative}
        strokeWidth="1"
        strokeDasharray="4,3"
      />
      <line
        x1={dividerX}
        y1={yOf(afterAvg)}
        x2={W}
        y2={yOf(afterAvg)}
        stroke={JT.positive}
        strokeWidth="1"
        strokeDasharray="4,3"
      />

      {/* FIX 2: Score line -- terracotta #C4704B, 1.5px, NO dots */}
      <polyline
        points={points}
        fill="none"
        stroke={JT.accent}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Vertical dashed divider at start date */}
      <line
        x1={dividerX}
        y1="0"
        x2={dividerX}
        y2={H}
        stroke={JT.textMuted}
        strokeWidth="1"
        strokeDasharray="2,2"
      />

      {/* Before / After labels */}
      <text x={dividerX / 2} y="12" textAnchor="middle" fontSize="9" fill={JT.textSecondary}>
        Before
      </text>
      <text
        x={dividerX + (W - dividerX) / 2}
        y="12"
        textAnchor="middle"
        fontSize="9"
        fill={JT.textSecondary}
      >
        After
      </text>

      {/* Average value annotations */}
      <text x="4" y={yOf(beforeAvg) - 4} fontSize="8" fill={JT.negative}>
        {beforeAvg.toFixed(1)} avg
      </text>
      <text x={W - 4} y={yOf(afterAvg) - 4} textAnchor="end" fontSize="8" fill={JT.positive}>
        {afterAvg.toFixed(1)} avg
      </text>
    </svg>
  );
}

// -- Consistency Calendar -------------------------------------------------
// Compact flowing grid — one 16px square per day, no week structure.

const SQ = 16;
const SQ_GAP = 4;

function ConsistencyCalendar({
  completedDates,
  today,
}: {
  completedDates: string[];
  today: string;
}) {
  const completedSet = new Set(completedDates);
  const days = getMonthDays(today);

  return (
    <div>
      {/* Flowing square grid — wraps naturally within the card */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: SQ_GAP }}>
        {days.map((day) => {
          const completed = completedSet.has(day.date);

          let bg: string;
          let opacity = 1;
          if (day.isFuture) {
            bg = JT.surface;
            opacity = 0.4;
          } else if (completed) {
            bg = JT.positive;
          } else {
            bg = JT.negativeLight;
          }

          return (
            <div
              key={day.date}
              style={{
                width: SQ,
                height: SQ,
                borderRadius: 4,
                background: bg,
                opacity,
                ...(day.isToday
                  ? { border: `1.5px solid ${JT.accent}`, boxSizing: 'border-box' as const }
                  : {}),
              }}
            />
          );
        })}
      </div>

      {/* Legend — 10px squares + 10px text, 12px gap, 10px margin-top */}
      <div
        style={{
          display: 'flex',
          gap: 12,
          marginTop: 10,
          alignItems: 'center',
        }}
      >
        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          <div style={{ width: 10, height: 10, borderRadius: 3, background: JT.positive }} />
          <span style={{ fontSize: 10, color: JT.textMuted }}>Active</span>
        </div>
        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          <div style={{ width: 10, height: 10, borderRadius: 3, background: JT.negativeLight }} />
          <span style={{ fontSize: 10, color: JT.textMuted }}>Missed</span>
        </div>
      </div>
    </div>
  );
}

// -- Main Component -------------------------------------------------------

export function HabitDetail({
  title,
  category,
  startDate,
  scoreLift,
  avgActive,
  avgInactive,
  completedDays,
  totalDays,
  scoreData,
  interpretation,
  confoundingFactors,
  completedDates,
  today,
  onBack,
}: HabitDetailProps) {
  const todayISO = today ?? new Date().toISOString().split('T')[0];
  const consistencyPct = totalDays > 0 ? Math.round((completedDays / totalDays) * 100) : 0;
  const liftStr = scoreLift >= 0 ? `+${scoreLift.toFixed(1)}` : scoreLift.toFixed(1);

  return (
    <div style={{ padding: '16px 24px 40px', color: JT.text }}>
      {/* Back navigation */}
      <div
        style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20, cursor: 'pointer' }}
        onClick={onBack}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' && onBack) onBack(); }}
      >
        <span style={{ fontSize: 16, color: JT.textSecondary }}>&#8592;</span>
        <span style={{ fontSize: 13, color: JT.textSecondary }}>Actions</span>
      </div>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div
          style={{
            fontSize: 10,
            color: JT.textMuted,
            fontWeight: 600,
            marginBottom: 4,
            textTransform: 'uppercase',
            letterSpacing: 0.5,
          }}
        >
          {category} &middot; Habit &middot; Since {formatSinceDate(startDate)}
        </div>
        <div style={{ fontSize: 22, fontWeight: 700, lineHeight: 1.25 }}>{title}</div>
      </div>

      {/* ---- Impact + Consistency cards ---- */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 18 }}>
        {/* FIX 1: Impact card -- solid olive #7A8F6B background, all text white */}
        <div
          style={{
            flex: 1,
            background: JT.positive,
            borderRadius: 14,
            padding: 16,
            color: '#fff',
          }}
        >
          <div style={{ fontSize: 10, opacity: 0.8, marginBottom: 2 }}>Score impact</div>
          <div style={{ fontSize: 34, fontWeight: 700, lineHeight: 1 }}>{liftStr}</div>
          <div style={{ fontSize: 10, opacity: 0.8, marginTop: 4 }}>avg lift on active days</div>
        </div>

        {/* Consistency card -- white with border (unchanged) */}
        <div
          style={{
            flex: 1,
            background: JT.card,
            borderRadius: 14,
            padding: 16,
            border: `1px solid ${JT.border}`,
          }}
        >
          <div style={{ fontSize: 10, color: JT.textMuted, marginBottom: 2 }}>Consistency</div>
          <div style={{ fontSize: 34, fontWeight: 700, lineHeight: 1, color: JT.text }}>
            {consistencyPct}%
          </div>
          <div style={{ fontSize: 10, color: JT.textMuted, marginTop: 4 }}>
            {completedDays} of {totalDays} days
          </div>
        </div>
      </div>

      {/* ---- Before / After chart card ---- */}
      <div style={{ background: JT.card, borderRadius: 16, padding: 16, marginBottom: 18 }}>
        {/* FIX 3: Title = "Daily score over time", subtitle = "Before vs after starting" */}
        <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 3 }}>Daily score over time</div>
        <div style={{ fontSize: 11, color: JT.textMuted, marginBottom: 12 }}>
          Before vs after starting
        </div>
        <BeforeAfterChart scoreData={scoreData} startDate={startDate} />
      </div>

      {/* ---- AI interpretation ---- */}
      <div
        style={{
          background: JT.secondaryLight,
          borderRadius: 16,
          padding: '14px 16px',
          marginBottom: 18,
        }}
      >
        <div
          style={{
            fontSize: 10,
            fontWeight: 600,
            color: JT.secondary,
            textTransform: 'uppercase',
            letterSpacing: 0.5,
            marginBottom: 6,
          }}
        >
          AI interpretation
        </div>
        <p style={{ fontSize: 13, lineHeight: 1.55, margin: 0, color: JT.text }}>
          {interpretation}
        </p>
      </div>

      {/* ---- Confounding factors ---- */}
      {confoundingFactors.length > 0 && (
        <div
          style={{
            background: JT.card,
            borderRadius: 16,
            padding: '14px 16px',
            marginBottom: 18,
            border: `1px solid ${JT.border}`,
          }}
        >
          <div style={{ fontSize: 11, fontWeight: 600, color: JT.textSecondary, marginBottom: 8 }}>
            Other factors in this period
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {confoundingFactors.map((f) => (
              <span
                key={f}
                style={{
                  fontSize: 11,
                  padding: '4px 10px',
                  background: JT.surface,
                  borderRadius: 8,
                  color: JT.textSecondary,
                }}
              >
                {f}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ---- Consistency calendar ---- */}
      <div style={{ background: JT.card, borderRadius: 16, padding: '14px 16px' }}>
        <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 10 }}>This month</div>
        <ConsistencyCalendar completedDates={completedDates} today={todayISO} />
      </div>
    </div>
  );
}
