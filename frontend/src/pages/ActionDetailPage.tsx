/**
 * ActionDetailPage — routes to HabitDetail or CompletableDetail
 * based on the action's type.
 *
 * Route: /actions/:id
 * Fetches action data and renders the appropriate detail component.
 */
import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { HabitDetail } from '../components/actions/HabitDetail';
import { CompletableDetail } from '../components/actions/CompletableDetail';

// ── Placeholder data ────────────────────────────────────────────────────
// In a real implementation, this would come from an API call using the action ID.
// For now, we use static demo data matching the wireframe.

const DEMO_HABIT = {
  title: 'Prioritise daily exercise',
  category: 'Health',
  startDate: '2026-02-08',
  scoreLift: 1.4,
  avgActive: 6.5,
  avgInactive: 5.1,
  completedDays: 18,
  totalDays: 23,
  scoreData: [
    { date: '2026-01-25', score: 3.2 },
    { date: '2026-01-27', score: 3.8 },
    { date: '2026-01-29', score: 3.0 },
    { date: '2026-01-31', score: 4.4 },
    { date: '2026-02-02', score: 3.6 },
    { date: '2026-02-04', score: 4.6 },
    { date: '2026-02-06', score: 3.8 },
    { date: '2026-02-08', score: 4.6 },
    { date: '2026-02-10', score: 5.4 },
    { date: '2026-02-12', score: 5.8 },
    { date: '2026-02-14', score: 6.2 },
    { date: '2026-02-16', score: 6.6 },
    { date: '2026-02-18', score: 6.3 },
    { date: '2026-02-20', score: 6.8 },
    { date: '2026-02-22', score: 7.2 },
    { date: '2026-02-24', score: 7.4 },
    { date: '2026-02-26', score: 7.6 },
    { date: '2026-02-28', score: 7.8 },
    { date: '2026-03-02', score: 7.6 },
    { date: '2026-03-04', score: 7.8 },
  ],
  interpretation:
    "You've never scored below 5.5 on an exercise day. On non-exercise days, your range is 2\u20137. Exercise doesn't make you feel great \u2014 it prevents crashes. It's your floor, not your ceiling.",
  confoundingFactors: ['Started sertraline', 'Office routine', 'Phone boundaries'],
  habitLogs: [
    { log_date: '2026-03-01', completed: true },
    { log_date: '2026-03-02', completed: true },
    { log_date: '2026-03-03', completed: true },
    { log_date: '2026-03-04', completed: false },
    { log_date: '2026-03-05', completed: true },
    { log_date: '2026-03-06', completed: true },
    { log_date: '2026-03-07', completed: true },
    { log_date: '2026-03-08', completed: true },
  ],
};

const DEMO_COMPLETABLE = {
  actionId: 1,
  title: 'Have the scope conversation with James',
  category: 'Career',
  createdDate: '2026-02-24',
  completed: false,
  mentionCount: 4,
  observation:
    'This has come up 4 times in your journal. Each time you\'ve identified a reason to delay \u2014 "waiting for the right moment", "too busy", "finding reasons." The pattern is avoidance, not timing. The conversation doesn\'t need to resolve everything \u2014 it just needs to happen.',
  milestones: [
    { text: 'Have the conversation', date: 'Overdue', done: false },
  ],
};

// ── Page Component ──────────────────────────────────────────────────────

export default function ActionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const handleBack = () => {
    navigate(-1);
  };

  // TODO: fetch real action data by id from API
  // For now, route based on URL convention: ids starting with "h" = habit, "c" = completable
  // Or default to completable for numeric ids
  const isHabit = id?.startsWith('h');

  if (isHabit) {
    return (
      <HabitDetail
        {...DEMO_HABIT}
        onBack={handleBack}
      />
    );
  }

  return (
    <CompletableDetail
      {...DEMO_COMPLETABLE}
      actionId={Number(id) || 1}
      onBack={handleBack}
      onMarkDone={() => {
        // TODO: call API to mark action as done
        console.log('Mark done:', id);
      }}
    />
  );
}
