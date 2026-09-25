"use client";

import { useEffect, useState } from "react";
import {
  EntityResolutionApiError,
  entityResolutionApi,
} from "@/lib/entity-resolution/api-client";
import type { ResolvedEntityDetail as ResolvedEntityDetailData } from "@/lib/entity-resolution/contracts";

type DetailState =
  | { status: "loading" }
  | { status: "unauthorized" }
  | { status: "not-found" }
  | { status: "error"; message: string }
  | { status: "ready"; detail: ResolvedEntityDetailData };

function formatDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString();
}

// CDD-085 G-R3 §20/§24/§28: the resolved-identity detail surface -- read
// only, structurally distinct from the steward triage queue
// (EntityResolutionWorkspace), showing every governed source record that
// resolved into this EnterpriseEntity, including RESOLVED ones the queue
// deliberately never surfaces. Never implies the underlying DQ value
// disagreement (e.g. Country of Origin) is itself resolved -- entity
// identity and field-value quality are two separate governed questions.
export function ResolvedEntityDetail({ entityId }: { entityId: string }) {
  const [state, setState] = useState<DetailState>({ status: "loading" });

  // Mirrors case-detail-panel.tsx's own established effect pattern: the
  // effect body chains .then()/.catch() directly (state updates deferred
  // into the promise callback, never called synchronously within the
  // effect's own body) with an AbortController for cleanup. Loading state
  // is never reset synchronously inside the effect (the parent route
  // remounts this component fresh via key={entityId} on every entity
  // switch, so the initial "loading" state is always correct on mount).
  useEffect(() => {
    const controller = new AbortController();
    entityResolutionApi
      .resolvedEntity(entityId, controller.signal)
      .then((detail) => {
        setState({ status: "ready", detail });
      })
      .catch((error: unknown) => {
        if (error instanceof Error && error.name === "AbortError") return;
        if (error instanceof EntityResolutionApiError) {
          if (error.problem.code === "AUTH_REQUIRED" || error.status === 401) {
            setState({ status: "unauthorized" });
            return;
          }
          if (error.status === 404) {
            setState({ status: "not-found" });
            return;
          }
          setState({ status: "error", message: error.problem.message });
          return;
        }
        setState({
          status: "error",
          message: "Unable to load resolved entity.",
        });
      });
    return () => controller.abort();
  }, [entityId]);

  if (state.status === "loading") {
    return (
      <div className="panel" role="status">
        Loading resolved entity…
      </div>
    );
  }
  if (state.status === "unauthorized") {
    return (
      <div className="panel">Sign in is required to view this entity.</div>
    );
  }
  if (state.status === "not-found") {
    return (
      <div className="panel">
        No governed resolved identity was found for this entity.
      </div>
    );
  }
  if (state.status === "error") {
    return <div className="panel error-summary">{state.message}</div>;
  }

  const { detail } = state;

  return (
    <div
      className="panel"
      style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
    >
      <div>
        <span className="eyebrow">Resolved Enterprise Entity</span>
        <h2 style={{ marginTop: "0.25rem" }}>
          {detail.enterprise_entity_name}
        </h2>
      </div>
      <p style={{ color: "var(--muted)" }}>
        Governed identity resolution shown here does not by itself imply any
        field-value quality condition on this entity is resolved.
      </p>
      {detail.records.map((record) => (
        <div key={record.understanding_key} className="panel obs-gate-card">
          <span className="eyebrow">{record.outcome}</span>
          <p>
            Business confidence: {record.business_confidence} · Produced{" "}
            {formatDate(record.produced_at)}
          </p>
          {record.narrative_explanation ? (
            <p>{record.narrative_explanation}</p>
          ) : null}
          {record.structured_reasons.length > 0 ? (
            <ul>
              {record.structured_reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          ) : null}
          <ul>
            {record.source_representations.map((source) => (
              <li key={source.source_object_id}>
                {source.source_system_name} — {source.source_object_name}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
