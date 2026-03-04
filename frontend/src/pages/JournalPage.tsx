/**
 * Journal V3 — Chat-first journal page.
 *
 * Tabs: Journal | Insights | Life Map
 * Journal tab: Trend chart + Chat thread + Input
 * Insights tab: Patterns + Correlations + Synthesis (Phase 2 will add sub-tabs)
 * Life Map tab: Life domain radar
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { WellnessTimeline } from '../components/journal/WellnessTimeline';
import { JournalInsights } from '../components/journal/JournalInsights';
import { LifeDomainRadar } from '../components/journal/LifeDomainRadar';
import { CorrelationChart } from '../components/journal/CorrelationChart';
import { SynthesisCard } from '../components/journal/SynthesisCard';
import { ChatThread } from '../components/journal/ChatThread';
import { ChatInput } from '../components/journal/ChatInput';
import { DailyScoreCard } from '../components/journal/DailyScoreCard';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Card } from '../components/ui/Card';
import { getScoreHistory } from '../api/wellnessScore';
import { getJournalPatterns } from '../api/journalPatterns';
import { getCurrentDomainScores, getDomainScoreHistory } from '../api/lifeDomains';
import { getMilestones, getWeeklySynthesis, getWeeklyPhases, exportJournalData } from '../api/milestones';
import {
  sendMessage,
  confirmDailyScore,
  getSessions,
  getSessionMessages,
} from '../api/journalChat';
import type { WellnessScore } from '../types/WellnessScore';
import type { LifeDomainScoreData } from '../types/LifeDomain';
import type { JournalPatternData } from '../types/JournalFactors';
import type { MilestoneData, PhaseData } from '../api/milestones';
import type { SessionGroup, ChatMessageData } from '../types/JournalChat';

function todayISO(): string {
  return new Date().toISOString().split('T')[0];
}

type Tab = 'journal' | 'insights' | 'lifemap';

const TABS: { key: Tab; label: string }[] = [
  { key: 'journal', label: 'Journal' },
  { key: 'insights', label: 'Insights' },
  { key: 'lifemap', label: 'Life Map' },
];

// Score proposal detection: match "around a X" or "around a X.X" patterns
const SCORE_PROPOSAL_REGEX = /around a (\d+(?:\.\d)?)/i;

function parseProposedScore(text: string): number | null {
  const match = text.match(SCORE_PROPOSAL_REGEX);
  if (match) {
    const score = parseFloat(match[1]);
    if (score >= 1 && score <= 10) {
      // Round to nearest 0.5
      return Math.round(score * 2) / 2;
    }
  }
  return null;
}

export default function JournalPage() {
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>('journal');

  // Chat state
  const [sessionGroups, setSessionGroups] = useState<SessionGroup[]>([]);
  const [inputText, setInputText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState<number | undefined>(undefined);
  const abortRef = useRef<AbortController | null>(null);

  // Score confirmation state: { [sessionId]: { proposed, confirmed, confirming } }
  const [scoreStates, setScoreStates] = useState<
    Record<number, { proposed: number; confirmed: boolean; confirming: boolean }>
  >({});

  // Shared data
  const [scoreHistory, setScoreHistory] = useState<WellnessScore[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>(todayISO());
  const [milestones, setMilestones] = useState<MilestoneData[]>([]);
  const [phases, setPhases] = useState<PhaseData[]>([]);

  // Life domains
  const [domainScores, setDomainScores] = useState<LifeDomainScoreData | null>(null);
  const [domainComparison, setDomainComparison] = useState<Record<string, number> | null>(null);

  // Patterns / insights
  const [patterns, setPatterns] = useState<JournalPatternData[]>([]);
  const [weeklySynthesis, setWeeklySynthesis] = useState<Record<string, any> | null>(null);

  const todayScore = scoreHistory.find((s) => s.score_date === todayISO());

  // ── Load initial data ──────────────────────────────────────────

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [
        sessionsRes, historyRes, domainRes, domainHistRes,
        patternsRes, milestonesRes, synthesisRes, phasesRes,
      ] = await Promise.allSettled([
        getSessions(30),
        getScoreHistory(30),
        getCurrentDomainScores(),
        getDomainScoreHistory(30),
        getJournalPatterns(),
        getMilestones(),
        getWeeklySynthesis(),
        getWeeklyPhases(30),
      ]);

      // Build session groups from loaded sessions
      if (sessionsRes.status === 'fulfilled') {
        const sessions = sessionsRes.value;
        const groups: SessionGroup[] = [];

        for (const s of sessions) {
          try {
            const messages = await getSessionMessages(s.id);
            groups.push({
              session_id: s.id,
              started_at: s.started_at,
              daily_score: s.daily_score,
              score_confirmed: s.daily_score !== null,
              messages: messages.map((m) => ({
                id: m.id,
                role: m.role,
                content: m.content,
                created_at: m.created_at,
              })),
            });

            // Track score state for sessions with confirmed scores
            if (s.daily_score !== null) {
              setScoreStates((prev) => ({
                ...prev,
                [s.id]: { proposed: s.daily_score!, confirmed: true, confirming: false },
              }));
            }

            // Track the most recent session
            if (groups.length === 1) {
              setCurrentSessionId(s.id);
            }
          } catch {
            // Session message fetch failed — skip
          }
        }

        // Reverse so oldest is first (sessions come newest-first from API)
        setSessionGroups(groups.reverse());
      }

      if (historyRes.status === 'fulfilled') {
        setScoreHistory(historyRes.value);
      }

      if (domainRes.status === 'fulfilled') {
        setDomainScores(domainRes.value);
      }

      if (domainHistRes.status === 'fulfilled') {
        const hist = domainHistRes.value;
        if (hist.length > 0) {
          setDomainComparison(hist[0].scores);
        }
      }

      if (patternsRes.status === 'fulfilled') {
        setPatterns(patternsRes.value);
      }

      if (milestonesRes.status === 'fulfilled') {
        setMilestones(milestonesRes.value);
      }

      if (synthesisRes.status === 'fulfilled') {
        setWeeklySynthesis(synthesisRes.value.data);
      }

      if (phasesRes.status === 'fulfilled') {
        setPhases(phasesRes.value);
      }
    } catch (err) {
      console.error('Failed to load journal data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ── Send message ───────────────────────────────────────────────

  const handleSend = useCallback(() => {
    const text = inputText.trim();
    if (!text || isStreaming) return;

    setInputText('');
    setIsStreaming(true);

    // Optimistically add user message to the UI
    const userMsg: ChatMessageData = {
      id: null,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };

    // Add streaming placeholder for assistant
    const streamingMsg: ChatMessageData = {
      id: null,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
      isStreaming: true,
    };

    setSessionGroups((prev) => {
      const groups = [...prev];
      if (groups.length > 0 && groups[groups.length - 1].session_id === currentSessionId) {
        // Add to existing session
        const last = { ...groups[groups.length - 1] };
        last.messages = [...last.messages, userMsg, streamingMsg];
        groups[groups.length - 1] = last;
      } else {
        // New session will be created by the backend — add a temporary group
        groups.push({
          session_id: currentSessionId ?? -1,
          started_at: new Date().toISOString(),
          daily_score: null,
          score_confirmed: false,
          messages: [userMsg, streamingMsg],
        });
      }
      return groups;
    });

    // Start SSE stream
    const controller = sendMessage(
      text,
      currentSessionId,
      // onToken
      (token) => {
        setSessionGroups((prev) => {
          const groups = [...prev];
          const lastGroup = { ...groups[groups.length - 1] };
          const msgs = [...lastGroup.messages];
          const lastMsg = { ...msgs[msgs.length - 1] };
          lastMsg.content += token;
          msgs[msgs.length - 1] = lastMsg;
          lastGroup.messages = msgs;
          groups[groups.length - 1] = lastGroup;
          return groups;
        });
      },
      // onDone
      (data) => {
        setIsStreaming(false);
        setCurrentSessionId(data.session_id);

        // Finalize the streaming message
        setSessionGroups((prev) => {
          const groups = [...prev];
          const lastGroup = { ...groups[groups.length - 1] };

          // Update session_id if it was temporary
          lastGroup.session_id = data.session_id;

          const msgs = [...lastGroup.messages];
          const lastMsg = { ...msgs[msgs.length - 1] };
          lastMsg.id = data.message_id;
          lastMsg.isStreaming = false;
          msgs[msgs.length - 1] = lastMsg;
          lastGroup.messages = msgs;
          groups[groups.length - 1] = lastGroup;

          // Check if the assistant proposed a score
          const proposedScore = parseProposedScore(lastMsg.content);
          if (proposedScore !== null && !scoreStates[data.session_id]?.confirmed) {
            setScoreStates((ss) => ({
              ...ss,
              [data.session_id]: { proposed: proposedScore, confirmed: false, confirming: false },
            }));
          }

          return groups;
        });
      },
      // onError
      (error) => {
        setIsStreaming(false);
        console.error('Chat stream error:', error);

        // Update streaming message with error
        setSessionGroups((prev) => {
          const groups = [...prev];
          const lastGroup = { ...groups[groups.length - 1] };
          const msgs = [...lastGroup.messages];
          const lastMsg = { ...msgs[msgs.length - 1] };
          lastMsg.content = lastMsg.content || 'Failed to get a response. Please try again.';
          lastMsg.isStreaming = false;
          msgs[msgs.length - 1] = lastMsg;
          lastGroup.messages = msgs;
          groups[groups.length - 1] = lastGroup;
          return groups;
        });
      },
    );

    abortRef.current = controller;
  }, [inputText, isStreaming, currentSessionId, scoreStates]);

  // ── Score confirmation ─────────────────────────────────────────

  const handleScoreConfirm = useCallback(
    async (sessionId: number, score: number) => {
      setScoreStates((prev) => ({
        ...prev,
        [sessionId]: { ...prev[sessionId], confirming: true },
      }));

      try {
        await confirmDailyScore(sessionId, score);

        setScoreStates((prev) => ({
          ...prev,
          [sessionId]: { proposed: score, confirmed: true, confirming: false },
        }));

        // Update the session group
        setSessionGroups((prev) =>
          prev.map((g) =>
            g.session_id === sessionId
              ? { ...g, daily_score: score, score_confirmed: true }
              : g,
          ),
        );

        // Refresh score history
        try {
          const history = await getScoreHistory(30);
          setScoreHistory(history);
        } catch {
          // Non-fatal
        }
      } catch (err) {
        console.error('Score confirmation failed:', err);
        setScoreStates((prev) => ({
          ...prev,
          [sessionId]: { ...prev[sessionId], confirming: false },
        }));
      }
    },
    [],
  );

  // ── Export ──────────────────────────────────────────────────────

  const handleExport = async () => {
    try {
      const data = await exportJournalData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `journal-export-${todayISO()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  const handleDateSelect = (date: string) => {
    setSelectedDate(date);
  };

  // ── Render ─────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Page header */}
      <div className="px-4 pt-4 pb-2">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-bold text-gray-900">Journal</h1>
          <div className="flex items-center gap-2">
            {todayScore && (
              <>
                <div className="text-right">
                  <div className="text-xs text-gray-400">Today</div>
                  <div
                    className={`text-sm font-semibold ${
                      todayScore.score >= 70
                        ? 'text-green-600'
                        : todayScore.score >= 50
                          ? 'text-amber-500'
                          : 'text-red-500'
                    }`}
                  >
                    {Math.round(todayScore.score)}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="px-4 flex gap-1 mb-1">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
              activeTab === tab.key
                ? 'bg-gray-200 text-gray-800'
                : 'text-gray-400 hover:text-gray-600'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden flex flex-col" style={{ minHeight: 0 }}>
        {/* ── JOURNAL TAB ── */}
        {activeTab === 'journal' && (
          <div className="flex flex-col h-full">
            {/* Trend chart */}
            {scoreHistory.length > 0 && (
              <div className="px-4 py-2 border-b border-gray-100">
                <WellnessTimeline
                  scores={scoreHistory}
                  selectedDate={selectedDate}
                  onDateSelect={handleDateSelect}
                  milestones={milestones}
                  phases={phases}
                  compact
                />
              </div>
            )}

            {/* Chat thread */}
            <ChatThread
              sessionGroups={sessionGroups}
              renderScoreCard={(sessionId, _dailyScore) => {
                const state = scoreStates[sessionId];
                if (!state) return null;

                return (
                  <DailyScoreCard
                    key={`score-${sessionId}`}
                    proposedScore={state.proposed}
                    confirmed={state.confirmed}
                    onConfirm={(score) => handleScoreConfirm(sessionId, score)}
                    confirming={state.confirming}
                  />
                );
              }}
            />

            {/* Chat input */}
            <ChatInput
              value={inputText}
              onChange={setInputText}
              onSend={handleSend}
              disabled={isStreaming}
            />
          </div>
        )}

        {/* ── INSIGHTS TAB ── */}
        {activeTab === 'insights' && (
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
            <JournalInsights />
            {patterns.length > 0 && <CorrelationChart patterns={patterns} />}

            {/* Timeline */}
            {scoreHistory.length > 0 && (
              <WellnessTimeline
                scores={scoreHistory}
                selectedDate={selectedDate}
                onDateSelect={handleDateSelect}
                milestones={milestones}
                phases={phases}
              />
            )}

            {/* Weekly synthesis */}
            {weeklySynthesis && Object.keys(weeklySynthesis).length > 0 && (
              <SynthesisCard synthesis={weeklySynthesis} type="weekly" />
            )}

            {/* Export button */}
            <div className="text-center pt-2">
              <button
                onClick={handleExport}
                className="text-xs text-gray-400 hover:text-gray-600 underline"
              >
                Export journal data
              </button>
            </div>
          </div>
        )}

        {/* ── LIFE MAP TAB ── */}
        {activeTab === 'lifemap' && (
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
            {domainScores ? (
              <Card>
                <h3 className="text-sm font-semibold text-gray-700 mb-3 text-center">
                  Life Domains
                </h3>
                <LifeDomainRadar
                  current={domainScores.scores}
                  comparison={domainComparison}
                  totalScore={domainScores.total_score}
                  size={320}
                />
              </Card>
            ) : (
              <Card>
                <div className="text-center py-10">
                  <div className="text-3xl mb-3">{'\uD83C\uDF10'}</div>
                  <p className="text-sm text-gray-400">
                    Life domain scores will appear after your first journal entry.
                  </p>
                </div>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
