'use client';

import { useState, useCallback, useRef, useEffect, type KeyboardEvent, type ChangeEvent } from 'react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled: boolean;
}

const MAX_ROWS = 4;
const LINE_HEIGHT = 24; // px, matching text-sm leading-6
const PADDING_Y = 20; // py-2.5 top + bottom = 20px

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const hasText = value.trim().length > 0;

  // Auto-resize textarea up to MAX_ROWS
  const adjustHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    // Reset to single row to measure scrollHeight accurately
    textarea.style.height = 'auto';

    const maxHeight = LINE_HEIGHT * MAX_ROWS + PADDING_Y;
    const newHeight = Math.min(textarea.scrollHeight, maxHeight);
    textarea.style.height = `${newHeight}px`;

    // Toggle overflow when content exceeds max lines
    textarea.style.overflowY = textarea.scrollHeight > maxHeight ? 'auto' : 'hidden';
  }, []);

  useEffect(() => {
    adjustHeight();
  }, [value, adjustHeight]);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue('');

    // Reset height after clearing
    requestAnimationFrame(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    });
  }, [value, disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const handleChange = useCallback((e: ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
  }, []);

  return (
    <div className="chat-input-bar">
      <div
        className={`
          flex items-end gap-2 rounded-card border border-border
          bg-surface px-3 py-1.5
          transition-all duration-fast
          focus-within:border-accent/50
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="Ask Copy Agent..."
          rows={1}
          aria-label="Message input"
          className={`
            flex-1 resize-none bg-transparent text-sm text-foreground
            placeholder:text-muted py-2.5 leading-6
            focus:outline-none
            ${disabled ? 'cursor-not-allowed' : ''}
          `}
          style={{ overflowY: 'hidden' }}
        />

        <button
          onClick={handleSend}
          disabled={disabled || !hasText}
          aria-label="Send message"
          className={`
            shrink-0 w-8 h-8 rounded-lg flex items-center justify-center
            mb-0.5 transition-all duration-fast
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent
            ${
              hasText && !disabled
                ? 'bg-accent text-accent-foreground hover:bg-accent/90 active:scale-95'
                : 'bg-elevated text-muted cursor-not-allowed'
            }
          `}
        >
          {/* Arrow-up icon */}
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M8 13V3M8 3L3.5 7.5M8 3L12.5 7.5"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}
