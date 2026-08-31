"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { EmptyState } from "@/components/design-system/empty-state";
import { OqiApiError, oqiApi } from "@/lib/oqi/api-client";
import type { CommandCenterResponse } from "@/lib/oqi/contracts";
import { RelianceHero } from "./reliance-hero";

// CDD-045 §7/§20: the OQI Command Center answers "can I rely on my
// enterprise knowledge?" from real, tenant-scoped governed counts. There is
// no score, gauge, or percentage anywhere in this component -- every
// number here is a direct, unmodified pass-through of
// GET /api/v1/oqi/command-center (CDD-045 §29 UI Truth Table).
type LoadState =
  | { status: "loading" }
  | { status: "loaded"; data: CommandCenterResponse }
  | { status: "unauthorized" }
  | { status: "error"; code: string };

export function CommandCenter() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    oqiApi
      .commandCenter(controller.signal)
      .then((data) => setState({ status: "loaded", data }))
      .catch((caught) => {
        if (controller.signal.aborted) return;
        if (caught instanceof OqiApiError) {
          if (caught.status === 401 || caught.status === 403) {
            setState({ status: "unauthorized" });
            return;
          }
          setState({ status: "error", code: caught.code });
          return;
        }
        setState({ status: "error", code: "UNKNOWN_ERROR" });
      });
    return () => controller.abort();
  }, []);

  if (state.status === "loading") {
    return (
      <EmptyState
        kind="loading"
        title="Loading Ontology Quality Intelligence"
        message="Retrieving governed Reliance state -- not yet determined."
      />
    );
  }

  if (state.status === "unauthorized") {
    return (
      <EmptyState
        kind="error"
        title="Not authorized to view Ontology Quality Intelligence"
        message="This does not indicate anything about the underlying Reliance state."
      />
    );
  }

  if (state.status === "error") {
    return (
      <EmptyState
        kind="error"
        title="Ontology Quality Intelligence is temporarily unavailable"
        message={`Backend unavailable (${state.code}). This is a technical failure, separate from the governed Reliance state.`}
      />
    );
  }

  const data = state.data;

  return (
    <div
      data-testid="oqi-command-center"
      style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}
    >
      <RelianceHero
        supported={data.reliance_supported_count}
        atRisk={data.reliance_at_risk_count}
        unknown={data.reliance_unknown_count}
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(14rem, 1fr))",
          gap: "1rem",
        }}
      >
        <Link
          className="panel"
          href="/quality/findings"
          style={{ display: "block" }}
        >
          <span className="eyebrow">Critical Dependencies At Risk</span>
          <h3 style={{ marginTop: "0.25rem" }}>
            {data.critical_dependencies_at_risk_count}
          </h3>
        </Link>

        <Link
          className="panel"
          href="/quality/findings?status=OPEN"
          style={{ display: "block" }}
        >
          <span className="eyebrow">Open Findings</span>
          <h3 style={{ marginTop: "0.25rem" }}>{data.open_findings_count}</h3>
        </Link>

        <Link
          className="panel"
          href="/quality/findings"
          style={{ display: "block" }}
        >
          <span className="eyebrow">Active Agent Investigations</span>
          <h3 style={{ marginTop: "0.25rem" }}>
            {data.active_agent_investigations_count}
          </h3>
        </Link>

        <Link
          className="panel"
          href="/quality/findings"
          style={{ display: "block" }}
        >
          <span className="eyebrow">Pending Human Authorization</span>
          <h3 style={{ marginTop: "0.25rem" }}>
            {data.pending_human_authorizations_count}
          </h3>
        </Link>
      </div>
    </div>
  );
}
