"use client";

import { useCallback, useEffect, useState } from "react";
import { signIn } from "@/lib/auth/browser-session";
import {
  EntityResolutionApiError,
  entityResolutionApi,
} from "@/lib/entity-resolution/api-client";
import type { CaseSummary } from "@/lib/entity-resolution/contracts";
import { CaseDetailPanel } from "./case-detail-panel";
import { CaseQueue, type OutcomeFilter } from "./case-queue";

type QueueState =
  | { status: "loading" }
  | { status: "unauthorized" }
  | { status: "error"; message: string }
  | { status: "ready"; items: CaseSummary[] };

async function loadQueue(
  outcome: OutcomeFilter,
  signal: AbortSignal,
): Promise<QueueState> {
  try {
    const result = await entityResolutionApi.queue(
      outcome === "all" ? undefined : outcome,
      signal,
    );
    return { status: "ready", items: result.items };
  } catch (error) {
    if (error instanceof EntityResolutionApiError) {
      if (error.problem.code === "AUTH_REQUIRED" || error.status === 401) {
        return { status: "unauthorized" };
      }
      return { status: "error", message: error.problem.message };
    }
    if (error instanceof Error && error.name === "AbortError") {
      throw error;
    }
    return {
      status: "error",
      message: "The Entity Resolution service could not be reached.",
    };
  }
}

export function EntityResolutionWorkspace() {
  const [outcomeFilter, setOutcomeFilter] = useState<OutcomeFilter>("all");
  const [queueState, setQueueState] = useState<QueueState>({
    status: "loading",
  });
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  // Loading is reset synchronously in the handlers that trigger a refetch
  // (changeOutcomeFilter / refreshQueue) rather than inside the effect
  // body itself -- matching how StudioClient's own retry button works.
  // The effect only ever sets state from its async result.
  const changeOutcomeFilter = useCallback((value: OutcomeFilter) => {
    setQueueState({ status: "loading" });
    setOutcomeFilter(value);
  }, []);

  const refreshQueue = useCallback(() => {
    setQueueState({ status: "loading" });
    setRefreshToken((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadQueue(outcomeFilter, controller.signal)
      .then(setQueueState)
      .catch((error: unknown) => {
        if (error instanceof Error && error.name === "AbortError") return;
        setQueueState({
          status: "error",
          message: "The Entity Resolution service could not be reached.",
        });
      });
    return () => controller.abort();
  }, [outcomeFilter, refreshToken]);

  if (queueState.status === "loading") {
    return (
      <div className="panel" role="status">
        Loading the resolution case queue…
      </div>
    );
  }

  if (queueState.status === "unauthorized") {
    return (
      <div className="panel" role="alert">
        <p style={{ fontWeight: 700 }}>Sign in required</p>
        <p style={{ color: "var(--muted)" }}>
          You must sign in to review Entity Resolution cases.
        </p>
        <button
          type="button"
          className="button"
          style={{ marginTop: "0.75rem" }}
          onClick={() => void signIn("/ontology-studio/entity-resolution")}
        >
          Sign in
        </button>
      </div>
    );
  }

  if (queueState.status === "error") {
    return (
      <div className="panel" role="alert">
        <p style={{ fontWeight: 700 }}>Entity Resolution service unavailable</p>
        <p style={{ color: "var(--muted)" }}>{queueState.message}</p>
        <button
          type="button"
          className="button"
          style={{ marginTop: "0.75rem" }}
          onClick={refreshQueue}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">Ontology Studio</span>
          <h1>Entity Resolution Steward</h1>
          <p>
            Review multi-attribute evidence, preview policy outcomes, and record
            steward decisions for supplier resolution cases.
          </p>
        </div>
      </div>
      <CaseQueue
        items={queueState.items}
        outcomeFilter={outcomeFilter}
        onOutcomeFilterChange={changeOutcomeFilter}
        selectedKey={selectedKey}
        onSelect={setSelectedKey}
      />
      {selectedKey && (
        <CaseDetailPanel
          // Remounts fresh on every case switch, so its own loading state
          // starts correctly without needing a synchronous reset inside
          // its effect.
          key={selectedKey}
          understandingKey={selectedKey}
          onDecided={() => {
            refreshQueue();
          }}
          onClose={() => setSelectedKey(null)}
        />
      )}
    </div>
  );
}
