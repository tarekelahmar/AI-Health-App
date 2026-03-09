/**
 * Journal V3 — Chat Input.
 *
 * Textarea with dynamic height, send arrow button.
 * Enter sends (Shift+Enter for newline). Disabled while assistant is responding.
 *
 * Based on reference-chat-ui.jsx input area pattern.
 */
import React, { useRef, useEffect, KeyboardEvent } from 'react';

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled?: boolean;
  placeholder?: string;
  /** Show "Rate your day" button */
  showRateDay?: boolean;
  /** Called when user taps "Rate your day" */
  onRateDay?: () => void;
}

export function ChatInput({
  value,
  onChange,
  onSend,
  disabled = false,
  placeholder = "What's on your mind...",
  showRateDay = false,
  onRateDay,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
    }
  }, [value]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) {
        onSend();
      }
    }
  };

  const canSend = value.trim().length > 0 && !disabled;

  return (
    <div className="px-4 py-3 border-t border-gray-200 bg-white">
      <div className="flex items-end gap-2">
        {showRateDay && onRateDay && (
          <button
            onClick={onRateDay}
            className="shrink-0 w-9 h-9 rounded-full flex items-center justify-center bg-amber-50 hover:bg-amber-100 text-amber-500 transition-colors"
            aria-label="Rate your day"
            title="Rate your day"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </button>
        )}
        <div className="flex-1 bg-gray-50 rounded-2xl border border-gray-200 px-4 py-2.5 focus-within:border-blue-300 transition-colors">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="w-full bg-transparent text-sm text-gray-800 placeholder-gray-400 resize-none outline-none disabled:opacity-50"
            style={{ minHeight: 20, maxHeight: 120 }}
          />
        </div>
        <button
          onClick={onSend}
          disabled={!canSend}
          className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 transition-all ${
            canSend
              ? 'bg-blue-600 hover:bg-blue-500 text-white'
              : 'bg-gray-100 text-gray-300'
          }`}
          aria-label="Send message"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
          >
            <line x1="12" y1="19" x2="12" y2="5" />
            <polyline points="5 12 12 5 19 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
