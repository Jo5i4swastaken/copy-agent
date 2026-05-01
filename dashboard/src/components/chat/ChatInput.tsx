'use client';

import {
  useState,
  useCallback,
  useRef,
  useEffect,
  type KeyboardEvent,
  type ChangeEvent,
} from 'react';

interface ChatInputProps {
  onSend: (message: string, files: File[], options: { thinking: boolean }) => void;
  disabled: boolean;
}

const MAX_ROWS = 4;
const LINE_HEIGHT = 24; // px, matching text-sm leading-6
const PADDING_Y = 20; // py-2.5 top + bottom = 20px

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [thinking, setThinking] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
    onSend(trimmed, files, { thinking });
    setValue('');
    setFiles([]);

    // Reset height after clearing
    requestAnimationFrame(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    });
  }, [value, disabled, onSend, files, thinking]);

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

  const handleChooseFiles = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFilesSelected = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const list = e.target.files ? Array.from(e.target.files) : [];
      setFiles(list);
    },
    [],
  );

  const handleRemoveFile = useCallback((name: string) => {
    setFiles((prev) => prev.filter((f) => f.name !== name));
  }, []);

  return (
    <div className="chat-input-bar">
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={handleFilesSelected}
        disabled={disabled}
      />

      <div
        className={`
          flex items-end gap-2 rounded-card border border-border
          bg-surface px-3 py-1.5
          transition-all duration-fast
          focus-within:border-accent/50
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <button
          type="button"
          onClick={handleChooseFiles}
          disabled={disabled}
          aria-label="Attach files"
          className={
            disabled
              ? 'shrink-0 w-8 h-8 rounded-lg flex items-center justify-center mb-0.5 bg-elevated text-muted cursor-not-allowed'
              : 'shrink-0 w-8 h-8 rounded-lg flex items-center justify-center mb-0.5 bg-elevated text-muted hover:text-foreground hover:bg-elevated/80'
          }
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M6 4.5V11a2 2 0 1 0 4 0V4a2.5 2.5 0 0 0-5 0v7a3.5 3.5 0 1 0 7 0V5"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>

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
          type="button"
          onClick={() => setThinking((v) => !v)}
          disabled={disabled}
          aria-label={thinking ? 'Disable thinking' : 'Enable thinking'}
          className={
            disabled
              ? 'shrink-0 px-2 h-8 rounded-lg mb-0.5 bg-elevated text-muted cursor-not-allowed text-xs'
              : thinking
                ? 'shrink-0 px-2 h-8 rounded-lg mb-0.5 bg-accent/20 text-foreground text-xs hover:bg-accent/30'
                : 'shrink-0 px-2 h-8 rounded-lg mb-0.5 bg-elevated text-muted text-xs hover:text-foreground hover:bg-elevated/80'
          }
        >
          Think
        </button>

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

      {files.length > 0 && (
        <div className="px-3 pt-2 flex flex-wrap gap-1">
          {files.map((file) => (
            <button
              key={file.name}
              type="button"
              onClick={() => handleRemoveFile(file.name)}
              className="text-[11px] px-2 py-1 rounded-full bg-elevated text-foreground-secondary hover:text-foreground"
              title="Remove attachment"
            >
              {file.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
