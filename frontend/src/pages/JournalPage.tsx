import React, { useState, useEffect, useCallback } from 'react';
import { WellnessScoreRing } from '../components/journal/WellnessScoreRing';
import { JournalForm } from '../components/journal/JournalForm';
import { CompanionResponse } from '../components/journal/CompanionResponse';
import { ScoreBreakdown } from '../components/journal/ScoreBreakdown';
import { WellnessTimeline } from '../components/journal/WellnessTimeline';
import { JournalInsights } from '../components/journal/JournalInsights';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Card } from '../components/ui/Card';
import { getCheckIn, upsertCheckIn } from '../api/checkins';
import { analyzeWithCompanion } from '../api/journalPatterns';
import { computeScore, getScoreHistory } from '../api/wellnessScore';
import type { CheckIn } from '../types/CheckIn';
import type { WellnessScore } from '../types/WellnessScore';
import type { CompanionAnalyzeResponse } from '../types/CompanionResponse';

function todayISO(): string {
  return new Date().toISOString().split('T')[0];
}

type Tab = 'today' | 'insights' | 'history';

const TABS: { key: Tab; label: string }[] = [
  { key: 'today', label: 'Today' },
  { key: 'insights', label: 'Insights' },
  { key: 'history', label: 'History' },
];

export default function JournalPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [checkIn, setCheckIn] = useState<CheckIn | null>(null);
  const [todayScore, setTodayScore] = useState<WellnessScore | null>(null);
  const [yesterdayScore, setYesterdayScore] = useState<number | null>(null);
  const [scoreHistory, setScoreHistory] = useState<WellnessScore[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>(todayISO());
  const [activeTab, setActiveTab] = useState<Tab>('today');
  const [companionResult, setCompanionResult] = useState<CompanionAnalyzeResponse | null>(null);
  const [analyzingCompanion, setAnalyzingCompanion] = useState(false);

  const userId = parseInt(localStorage.getItem('user_id') || '1', 10);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [checkinRes, historyRes] = await Promise.allSettled([
        getCheckIn(userId, todayISO()),
        getScoreHistory(30),
      ]);

      if (checkinRes.status === 'fulfilled') {
        const loaded = checkinRes.value;
        setCheckIn(loaded);

        // If there's already a companion response from a previous save, show it
        if (loaded.ai_response_text) {
          setCompanionResult({
            extraction_method: 'llm',
            depth_level: loaded.depth_level ?? 2,
            factors: loaded.behaviors_json || {},
            custom_factors: [],
            ai_inferred: loaded.ai_inferred_json as any ?? null,
            context_tags: loaded.context_tags_json as any ?? null,
            companion_response: {
              text: loaded.ai_response_text,
              pattern_referenced: false,
              discrepancy_noted: loaded.discrepancy_json?.flag ?? false,
            },
            discrepancies: loaded.discrepancy_json?.discrepancies ?? [],
          });
        }
      }

      if (historyRes.status === 'fulfilled') {
        const history = historyRes.value;
        setScoreHistory(history);

        const today = history.find((s) => s.score_date === todayISO());
        setTodayScore(today || null);

        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        const yesterdayISO = yesterday.toISOString().split('T')[0];
        const ys = history.find((s) => s.score_date === yesterdayISO);
        setYesterdayScore(ys ? ys.score : null);
      }
    } catch (err) {
      console.error('Failed to load journal data:', err);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSave = async (data: {
    overall_wellbeing: number;
    energy: number;
    mood: number;
    focus: number;
    connection: number;
    notes: string;
    behaviors_json: Record<string, any>;
  }) => {
    setSaving(true);
    try {
      const savedCheckIn = await upsertCheckIn({
        user_id: userId,
        checkin_date: todayISO(),
        overall_wellbeing: data.overall_wellbeing,
        energy: data.energy,
        mood: data.mood,
        focus: data.focus,
        connection: data.connection,
        notes: data.notes,
        behaviors_json: data.behaviors_json,
      });
      setCheckIn(savedCheckIn);

      // Compute wellness score
      const score = await computeScore(todayISO());
      setTodayScore(score);

      const history = await getScoreHistory(30);
      setScoreHistory(history);

      // Trigger companion analysis (non-blocking — show result when ready)
      setAnalyzingCompanion(true);
      try {
        const companion = await analyzeWithCompanion(savedCheckIn.id);
        setCompanionResult(companion);
      } catch (companionErr) {
        console.error('Companion analysis failed:', companionErr);
        // Not a critical failure — check-in was already saved successfully
      } finally {
        setAnalyzingCompanion(false);
      }
    } catch (err) {
      console.error('Failed to save check-in:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleDateSelect = (date: string) => {
    setSelectedDate(date);
  };

  const selectedScore = scoreHistory.find((s) => s.score_date === selectedDate) || todayScore;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Page header */}
      <div className="text-center">
        <h1 className="text-lg font-bold text-gray-900">Journal</h1>
        <p className="text-xs text-gray-500 mt-0.5">
          {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
        </p>
      </div>

      {/* Wellness Score Ring */}
      <Card className="flex flex-col items-center py-6">
        <WellnessScoreRing
          score={todayScore?.score ?? null}
          size={160}
          yesterdayScore={yesterdayScore}
        />
        {todayScore && (
          <div className="flex items-center gap-4 mt-3">
            {todayScore.objective_score != null && (
              <div className="text-center">
                <div className="text-xs text-gray-400">Wearable</div>
                <div className="text-sm font-semibold text-blue-600">
                  {Math.round(todayScore.objective_score)}
                </div>
              </div>
            )}
            {todayScore.subjective_score != null && (
              <div className="text-center">
                <div className="text-xs text-gray-400">Journal</div>
                <div className="text-sm font-semibold text-purple-600">
                  {Math.round(todayScore.subjective_score)}
                </div>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Tab navigation */}
      <div className="flex bg-gray-100 rounded-lg p-0.5">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 py-2 text-xs font-medium rounded-md transition-colors ${
              activeTab === tab.key
                ? 'bg-white text-gray-800 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'today' && (
        <>
          <JournalForm
            existingCheckIn={checkIn}
            onSave={handleSave}
            saving={saving}
          />

          {/* Companion response (appears after save) */}
          {analyzingCompanion && (
            <Card className="mt-3">
              <div className="flex items-center justify-center gap-2 py-3">
                <LoadingSpinner />
                <span className="text-xs text-gray-400">Analysing your entry...</span>
              </div>
            </Card>
          )}
          {!analyzingCompanion && companionResult && (
            <CompanionResponse result={companionResult} />
          )}

          {selectedScore && (
            <ScoreBreakdown factors={selectedScore.contributing_factors} />
          )}
        </>
      )}

      {activeTab === 'insights' && <JournalInsights />}

      {activeTab === 'history' && (
        <>
          {scoreHistory.length > 0 ? (
            <WellnessTimeline
              scores={scoreHistory}
              selectedDate={selectedDate}
              onDateSelect={handleDateSelect}
            />
          ) : (
            <div className="text-center py-10">
              <div className="text-3xl mb-3">{'\uD83D\uDCCA'}</div>
              <p className="text-sm text-gray-400">
                No history yet. Save your first check-in to start tracking.
              </p>
            </div>
          )}
          {selectedScore && selectedDate !== todayISO() && (
            <ScoreBreakdown factors={selectedScore.contributing_factors} />
          )}
        </>
      )}
    </div>
  );
}
