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
  onSend: (
    message: string,
    attachments?: { name: string; mime: string; data_base64: string }[],
  ) => void;
  disabled: boolean;
}

const MAX_ROWS = 4;
const LINE_HEIGHT = 24; // px, matching text-sm leading-6
const PADDING_Y = 20; // py-2.5 top + bottom = 20px

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState('');
  const [attachment, setAttachment] = useState<File | null>(null);
  const [attachmentPreviewUrl, setAttachmentPreviewUrl] = useState<string | null>(
    null,
  );
  const [attachmentTextPreview, setAttachmentTextPreview] = useState<string | null>(
    null,
  );
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const hasText = value.trim().length > 0;

  const clearAttachment = useCallback(() => {
    setAttachment(null);
    setAttachmentTextPreview(null);
    if (attachmentPreviewUrl) {
      URL.revokeObjectURL(attachmentPreviewUrl);
    }
    setAttachmentPreviewUrl(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [attachmentPreviewUrl]);

  useEffect(() => {
    return () => {
      if (attachmentPreviewUrl) {
        URL.revokeObjectURL(attachmentPreviewUrl);
      }
    };
  }, [attachmentPreviewUrl]);

  const formatBytes = useCallback((bytes: number) => {
    if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const idx = Math.min(
      units.length - 1,
      Math.floor(Math.log(bytes) / Math.log(1024)),
    );
    const value = bytes / 1024 ** idx;
    return `${idx === 0 ? Math.round(value) : value.toFixed(1)} ${units[idx]}`;
  }, []);

  const arrayBufferToBase64 = useCallback((buf: ArrayBuffer) => {
    let binary = '';
    const bytes = new Uint8Array(buf);
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }, []);

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
    void (async () => {
      const trimmed = value.trim();
      if (!trimmed || disabled) return;

      const attachments = attachment
        ? [
            {
              name: attachment.name,
              mime: attachment.type || 'application/octet-stream',
              data_base64: arrayBufferToBase64(await attachment.arrayBuffer()),
            },
          ]
        : undefined;

      onSend(trimmed, attachments);
      setValue('');
      clearAttachment();

      requestAnimationFrame(() => {
        if (textareaRef.current) {
          textareaRef.current.style.height = 'auto';
        }
      });
    })();
  }, [value, disabled, onSend, attachment, arrayBufferToBase64, clearAttachment]);

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

  const handleFileChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      void (async () => {
        const file = e.target.files?.[0] ?? null;
        if (!file) return;

        clearAttachment();
        setAttachment(file);

        const mime = file.type || '';
        if (mime.startsWith('image/')) {
          setAttachmentPreviewUrl(URL.createObjectURL(file));
        } else if (
          mime.startsWith('text/') ||
          mime === 'application/json' ||
          mime === 'application/xml'
        ) {
          const text = await file.text();
          setAttachmentTextPreview(text.slice(0, 4000));
        }
      })();
    },
    [clearAttachment],
  );

  const hasAttachment = attachment != null;
  const isImageAttachment = !!attachment && (attachment.type || '').startsWith('image/');
  const isTextAttachment = attachmentTextPreview != null;
  return (
    <div className="chat-input-bar">
      {hasAttachment ? (
        <div
          data-testid="attachment-preview"
          className="mb-2 rounded-card border border-border bg-elevated/40 px-3 py-2"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="text-sm text-foreground truncate">
                {attachment!.name}
              </div>
              <div className="text-xs text-muted">{formatBytes(attachment!.size)}</div>
            </div>
            <button
              type="button"
              aria-label="Remove attachment"
              onClick={clearAttachment}
              className="shrink-0 rounded-md px-2 py-1 text-xs text-muted hover:bg-elevated hover:text-foreground"
            >
              Remove
            </button>
          </div>

          {isImageAttachment && attachmentPreviewUrl ? (
            <div className="mt-2">
              <img
                data-testid="attachment-preview-image"
                src={attachmentPreviewUrl}
                alt="Attachment preview"
                className="max-h-48 w-auto rounded-md border border-border"
              />
            </div>
          ) : null}

          {isTextAttachment ? (
            <pre
              data-testid="attachment-preview-text"
              className="mt-2 max-h-48 overflow-auto rounded-md border border-border bg-surface p-2 text-xs text-foreground whitespace-pre-wrap"
            >
              {attachmentTextPreview}
            </pre>
          ) : null}

          {!isImageAttachment && !isTextAttachment ? (
            <div
              data-testid="attachment-preview-generic"
              className="mt-2 flex items-center gap-2 text-xs text-muted"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 16 16"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M6 4.5V11a2 2 0 0 0 4 0V4.8a1.6 1.6 0 0 0-3.2 0V10.9"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <span>Preview not available</span>
            </div>
          ) : null}
        </div>
      ) : null}

      <div
        className={`
          flex items-end gap-2 rounded-card border border-border
          bg-surface px-3 py-1.5
          transition-all duration-fast
          focus-within:border-accent/50
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="*/*"
          onChange={handleFileChange}
          className="hidden"
          aria-label="File attachment"
        />
        <button
          type="button"
          aria-label="Attach file"
          disabled={disabled}
          onClick={() => fileInputRef.current?.click()}
          className={`
            shrink-0 w-8 h-8 rounded-lg flex items-center justify-center
            mb-0.5 transition-all duration-fast
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent
            ${
              !disabled
                ? 'bg-elevated text-muted hover:text-foreground hover:bg-elevated/80'
                : 'bg-elevated text-muted cursor-not-allowed'
            }
          `}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M6 4.5V11a2 2 0 0 0 4 0V4.8a1.6 1.6 0 0 0-3.2 0V10.9"
              stroke="currentColor"
              strokeWidth="1.6"
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
