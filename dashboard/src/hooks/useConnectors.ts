"use client";

import { useState, useEffect, useCallback } from "react";

export interface ConnectorStatus {
  configured: boolean;
  detail: string;
}

export function useConnectors() {
  const [statuses, setStatuses] = useState<
    Record<string, ConnectorStatus>
  >({});
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch("/api/connectors");
      if (res.ok) {
        const data = await res.json();
        setStatuses(data);
      }
    } catch {
      // Silently fail — connector status is best-effort
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { statuses, isLoading, refresh };
}
