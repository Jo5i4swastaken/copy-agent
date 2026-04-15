"use client";

import { useState, useEffect, useMemo } from "react";
import { TransferCard } from "@/components/cross-channel/TransferCard";

interface Transfer {
  transfer_id: string;
  source_channel: string;
  target_channel: string;
  hypothesis: string;
  status: string;
  learning_text?: string;
  created_at?: string;
  result?: string;
}

const COLUMNS = [
  { key: "proposed", label: "Proposed", color: "border-yellow-500/30" },
  { key: "testing", label: "Testing", color: "border-blue-500/30" },
  { key: "confirmed", label: "Confirmed", color: "border-success/30" },
  { key: "rejected", label: "Rejected", color: "border-error/30" },
];

export default function CrossChannelPage() {
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch("/api/cross-channel");
        if (!res.ok) throw new Error("Failed to fetch transfers");
        const data = await res.json();
        setTransfers(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, []);

  const grouped = useMemo(() => {
    const map: Record<string, Transfer[]> = {
      proposed: [],
      testing: [],
      confirmed: [],
      rejected: [],
    };
    for (const t of transfers) {
      const key = t.status in map ? t.status : "proposed";
      map[key].push(t);
    }
    return map;
  }, [transfers]);

  return (
    <div className="animate-fade-in px-6 py-8 lg:px-10">
      <div className="mb-8">
        <h1 className="font-display text-2xl font-bold text-foreground">
          Cross-Channel Transfers
        </h1>
        <p className="mt-1 text-sm text-foreground-secondary">
          Track learning transfers between channels and their validation status.
        </p>
      </div>

      {error && (
        <div className="mb-6 rounded-card border border-error/30 bg-error-muted p-4 text-sm text-error" role="alert">
          {error}
        </div>
      )}

      {isLoading && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4" role="status">
          {COLUMNS.map((col) => (
            <div key={col.key}>
              <div className="skeleton mb-3 h-6 w-24 rounded" />
              <div className="skeleton h-32 w-full rounded-card" />
            </div>
          ))}
        </div>
      )}

      {!isLoading && !error && (
        <>
          {transfers.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-card border border-border-subtle bg-surface/50 px-6 py-16 text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-elevated">
                <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-muted" aria-hidden="true">
                  <path d="M4 14h20M14 4v20" strokeLinecap="round" />
                  <circle cx="7" cy="7" r="2" />
                  <circle cx="21" cy="21" r="2" />
                </svg>
              </div>
              <h2 className="mb-1 text-base font-semibold text-foreground">No transfers yet</h2>
              <p className="max-w-sm text-sm text-muted">
                When a learning reaches medium confidence, the agent will evaluate it for cross-channel transfer.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
              {COLUMNS.map((col) => (
                <div key={col.key}>
                  <div className={`mb-3 flex items-center gap-2 border-b-2 pb-2 ${col.color}`}>
                    <h2 className="text-sm font-semibold text-foreground">{col.label}</h2>
                    <span className="rounded-full bg-elevated px-2 py-0.5 text-xs text-muted">
                      {grouped[col.key].length}
                    </span>
                  </div>
                  <div className="space-y-3">
                    {grouped[col.key].map((transfer) => (
                      <TransferCard key={transfer.transfer_id} transfer={transfer} />
                    ))}
                    {grouped[col.key].length === 0 && (
                      <p className="py-4 text-center text-xs text-muted">None</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
