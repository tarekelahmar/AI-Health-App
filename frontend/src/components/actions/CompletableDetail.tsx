/**
 * CompletableDetail -- Completable-type action detail screen.
 *
 * Shows status, AI observation, journal mentions, and milestones
 * for a one-off completable action (not an ongoing habit).
 *
 * Design ref: journalling-wireframes-v2.jsx -> CompletableDetailScreen
 */
import React, { useState, useEffect } from 'react';
import { getActionMentions, type ActionMention } from '../../api/actions';

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

interface Milestone {
  text: string;
  date: string;
  done: boolean;
}

export interface CompletableDetailProps {
  /** Action ID (for fetching mentions) */
  actionId: number;
  /** Action title */
  title: string;
  /** e.g. "Career" */
  category: string;
  /** Creation date ISO string (YYYY-MM-DD) */
  createdDate: string;
  /** Whether the action is completed */
  completed: boolean;
  /** Completion date ISO string (YYYY-MM-DD), if completed */
  completedDate?: string;
  /** Number of times mentioned in journal */
  mentionCount: number;
  /** AI observation text */
  observation: string;
  /** Milestones for this action */
  milestones: Milestone[];
  /** Override today's date for testing (ISO string) */
  today?: string;
  /** Callback when "Mark done" is pressed */
  onMarkDone?: () => void;
  /** Back navigation callback */
  onBack?: () => void;
}

// -- Helpers --------------------------------------------------------------

function formatSinceDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  const date = new Date(y, m - 1, d);
  return date.toLocaleDateString('en-GB', { month: 'short', day: 'numeric' });
}

function daysBetween(fromISO: string, toISO: string): number {
  const from = new Date(fromISO);
  const to = new Date(toISO);
  return Math.floor((to.getTime() - from.getTime()) / (1000 * 60 * 60 * 24));
}

type ActionState = 'overdue' | 'active' | 'completed';

function getActionState(
  createdDate: string,
  completed: boolean,
  today: string,
): ActionState {
  if (completed) return 'completed';
  const age = daysBetween(createdDate, today);
  return age > 7 ? 'overdue' : 'active';
}

// -- Status Card ----------------------------------------------------------

function StatusCard({
  state,
  createdDate,
  completedDate,
  mentionCount,
  today,
  onMarkDone,
}: {
  state: ActionState;
  createdDate: string;
  completedDate?: string;
  mentionCount: number;
  today: string;
  onMarkDone?: () => void;
}) {
  const age = daysBetween(createdDate, today);

  // FIX 3: Background colour by state
  let bg: string;
  if (state === 'overdue') bg = JT.negativeLight;
  else if (state === 'completed') bg = JT.positiveLight;
  else bg = JT.card;

  // FIX 4: Status text wording
  let statusText: string;
  let statusColor: string;
  if (state === 'overdue') {
    statusText = `${age} days overdue`;
    statusColor = JT.negative;
  } else if (state === 'completed') {
    statusText = `Completed${completedDate ? ` ${formatSinceDate(completedDate)}` : ''}`;
    statusColor = JT.positive;
  } else {
    statusText = `Created ${age} days ago`;
    statusColor = JT.text;
  }

  return (
    <div
      style={{
        background: bg,
        borderRadius: 14,
        padding: 16,
        marginBottom: 18,
        ...(state === 'active' ? { border: `1px solid ${JT.border}` } : {}),
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: statusColor }}>{statusText}</div>
          <div style={{ fontSize: 11, color: JT.textSecondary, marginTop: 2 }}>
            Mentioned {mentionCount} time{mentionCount !== 1 ? 's' : ''} in journal
          </div>
        </div>
        {/* FIX 2: Mark done button — terracotta #C4704B */}
        {!completedDate && onMarkDone && (
          <button
            onClick={onMarkDone}
            style={{
              padding: '8px 16px',
              background: JT.accent,
              color: '#fff',
              borderRadius: 10,
              fontSize: 13,
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer',
            }}
          >
            Mark done
          </button>
        )}
      </div>
    </div>
  );
}

// -- Journal Mentions Section (FIX 5) ------------------------------------

function JournalMentions({ actionId, title }: { actionId: number; title: string }) {
  const [mentions, setMentions] = useState<ActionMention[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getActionMentions(actionId, title)
      .then((data) => {
        if (!cancelled) setMentions(data);
      })
      .catch(() => {
        if (!cancelled) setMentions([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [actionId, title]);

  return (
    <div
      style={{
        background: JT.card,
        borderRadius: 16,
        padding: '14px 16px',
        marginBottom: 18,
      }}
    >
      <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 12 }}>Journal mentions</div>

      {loading ? (
        <div style={{ fontSize: 13, color: JT.textMuted, textAlign: 'center', padding: '8px 0' }}>
          Loading...
        </div>
      ) : mentions.length === 0 ? (
        <div style={{ fontSize: 13, color: JT.textMuted, textAlign: 'center', padding: '8px 0' }}>
          No journal mentions yet.
        </div>
      ) : (
        mentions.map((m, i) => (
          <div
            key={m.message_id}
            style={{
              display: 'flex',
              gap: 10,
              marginBottom: i < mentions.length - 1 ? 12 : 0,
              paddingBottom: i < mentions.length - 1 ? 12 : 0,
              borderBottom: i < mentions.length - 1 ? `1px solid ${JT.border}` : 'none',
            }}
          >
            <div style={{ fontSize: 11, color: JT.textMuted, minWidth: 48 }}>{m.date}</div>
            <div
              style={{
                fontSize: 12,
                color: JT.textSecondary,
                lineHeight: 1.45,
                fontStyle: 'italic',
              }}
            >
              &ldquo;{m.excerpt}&rdquo;
            </div>
          </div>
        ))
      )}
    </div>
  );
}

// -- Main Component -------------------------------------------------------

export function CompletableDetail({
  actionId,
  title,
  category,
  createdDate,
  completed,
  completedDate,
  mentionCount,
  observation,
  milestones,
  today,
  onMarkDone,
  onBack,
}: CompletableDetailProps) {
  const todayISO = today ?? new Date().toISOString().split('T')[0];
  const state = getActionState(createdDate, completed, todayISO);

  // Header status label
  let headerStatus: string;
  let headerStatusColor: string;
  if (state === 'overdue') {
    headerStatus = 'Overdue';
    headerStatusColor = JT.negative;
  } else if (state === 'completed') {
    headerStatus = 'Completed';
    headerStatusColor = JT.positive;
  } else {
    headerStatus = 'Active';
    headerStatusColor = JT.textMuted;
  }

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
            color: headerStatusColor,
            fontWeight: 600,
            marginBottom: 4,
            textTransform: 'uppercase',
            letterSpacing: 0.5,
          }}
        >
          {category} &middot; {headerStatus} &middot; Since {formatSinceDate(createdDate)}
        </div>
        <div style={{ fontSize: 22, fontWeight: 700, lineHeight: 1.25 }}>{title}</div>
      </div>

      {/* Status card (FIX 2 + FIX 3 + FIX 4) */}
      <StatusCard
        state={state}
        createdDate={createdDate}
        completedDate={completedDate}
        mentionCount={mentionCount}
        today={todayISO}
        onMarkDone={onMarkDone}
      />

      {/* AI observation */}
      {observation && (
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
            AI observation
          </div>
          <p style={{ fontSize: 13, lineHeight: 1.55, margin: 0, color: JT.text }}>
            {observation}
          </p>
        </div>
      )}

      {/* Journal mentions (FIX 5) */}
      <JournalMentions actionId={actionId} title={title} />

      {/* Milestones */}
      {milestones.length > 0 && (
        <div style={{ background: JT.card, borderRadius: 16, padding: '14px 16px' }}>
          <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 12 }}>Milestones</div>
          {milestones.map((m, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                gap: 12,
                alignItems: 'center',
                marginBottom: i < milestones.length - 1 ? 12 : 0,
              }}
            >
              <div
                style={{
                  width: 18,
                  height: 18,
                  borderRadius: 9,
                  border: `2px solid ${m.done ? JT.positive : JT.negative}`,
                  background: m.done ? JT.positive : 'transparent',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                {m.done && (
                  <span style={{ color: '#fff', fontSize: 10, lineHeight: 1 }}>&#10003;</span>
                )}
              </div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{m.text}</div>
                <div
                  style={{
                    fontSize: 11,
                    color: m.done ? JT.positive : JT.negative,
                  }}
                >
                  {m.date}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
