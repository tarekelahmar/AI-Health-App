/**
 * Journal V3 — Chat Thread.
 *
 * Renders a scrollable list of messages grouped by session, with session dividers.
 * Handles streaming: the latest assistant message shows tokens appearing in real-time.
 *
 * Based on reference-chat-ui.jsx: SessionDivider + ChatMessage patterns.
 */
import React, { useEffect, useRef } from 'react';
import type { SessionGroup, ChatMessageData } from '../../types/JournalChat';

// ── Session Divider ───────────────────────────────────────────────

function SessionDivider({ date, time }: { date: string; time: string }) {
  return (
    <div className="flex items-center gap-3 my-5">
      <div className="flex-1 h-px bg-gray-200" />
      <span className="text-xs text-gray-400 font-medium tracking-wide">
        {date} · {time}
      </span>
      <div className="flex-1 h-px bg-gray-200" />
    </div>
  );
}

// ── Chat Message Bubble ──────────────────────────────────────────

function ChatMessage({ message }: { message: ChatMessageData }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div
        className={`max-w-[85%] px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? 'bg-blue-600 text-white rounded-2xl rounded-br-md'
            : 'bg-gray-100 text-gray-800 rounded-2xl rounded-bl-md border border-gray-200'
        }`}
      >
        {message.content}
        {message.isStreaming && (
          <span className="inline-block w-1.5 h-4 bg-gray-400 ml-0.5 animate-pulse rounded-sm" />
        )}
      </div>
    </div>
  );
}

// ── Format helpers ───────────────────────────────────────────────

function formatSessionDate(isoString: string): { date: string; time: string } {
  const d = new Date(isoString);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const sessionDay = new Date(d.getFullYear(), d.getMonth(), d.getDate());

  const diffDays = Math.floor((today.getTime() - sessionDay.getTime()) / (1000 * 60 * 60 * 24));

  let dateStr: string;
  if (diffDays === 0) {
    dateStr = 'Today';
  } else if (diffDays === 1) {
    dateStr = 'Yesterday';
  } else {
    dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  const timeStr = d.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });

  return { date: dateStr, time: timeStr };
}

// ── Main Component ───────────────────────────────────────────────

interface ChatThreadProps {
  sessionGroups: SessionGroup[];
  /** Inline children rendered at specific points (e.g., DailyScoreCard) */
  renderScoreCard?: (sessionId: number, proposedScore: number | null) => React.ReactNode;
  /** Inline card for weekly domain check-in, rendered after score card */
  renderDomainCard?: (sessionId: number) => React.ReactNode;
}

export function ChatThread({ sessionGroups, renderScoreCard, renderDomainCard }: ChatThreadProps) {
  const endRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [sessionGroups]);

  if (sessionGroups.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center py-20">
        <div className="text-center">
          <div className="text-3xl mb-3">{'\uD83D\uDCAC'}</div>
          <p className="text-sm text-gray-400">
            Start a conversation. How are you doing today?
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-3">
      {sessionGroups.map((group) => {
        const { date, time } = formatSessionDate(group.started_at);

        return (
          <div key={group.session_id}>
            <SessionDivider date={date} time={time} />
            {group.messages.map((msg, idx) => (
              <ChatMessage key={msg.id ?? `streaming-${idx}`} message={msg} />
            ))}
            {/* Score card after the last assistant message if score was proposed */}
            {renderScoreCard && renderScoreCard(group.session_id, group.daily_score)}
            {/* Domain check-in card after score card */}
            {renderDomainCard && renderDomainCard(group.session_id)}
          </div>
        );
      })}
      <div ref={endRef} />
    </div>
  );
}
