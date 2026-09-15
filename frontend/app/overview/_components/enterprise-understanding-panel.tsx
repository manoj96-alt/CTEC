"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState } from "@/components/design-system/empty-state";
import {
  StatusIndicator,
  type ObservatoryStatus,
} from "@/components/design-system/status-indicator";
import { OqiApiError, oqiApi } from "@/lib/oqi/api-client";
import type {
  CommandCenterResponse,
  FindingSummary,
} from "@/lib/oqi/contracts";

// CDD-080 §7-F/§8 of the governing prompt: mirrors the backend's own
// closed, four-value Criticality ordering (backend/app/domain/
// oqi_business_impact/dependency.py, `criticality_sort_key`) client-side
// -- never reinvented, never carries quantitative/monetary meaning.
const CRITICALITY_ORDER: Record<string, number> = {
  LOW: 0,
  MEDIUM: 1,
  HIGH: 2,
  CRITICAL: 3,
};

function relianceStatus(reliance: string | null): ObservatoryStatus {
  if (reliance === "RELIANCE_SUPPORTED") return "verified";
  if (reliance === "RELIANCE_AT_RISK") return "conflict";
  return "unknown";
}

type CommandCenterState =
  | { status: "loading" }
  | { status: "loaded"; data: CommandCenterResponse }
  | { status: "unauthorized" }
  | { status: "error"; code: string };

type SpotlightState =
  | { status: "loading" }
  | { status: "loaded"; finding: FindingSummary | null }
  | { status: "unauthorized" }
  | { status: "error"; code: string };

// CDD-080 §9: this is a Command-Center composition (page-specific), not a
// generic reusable primitive -- it implements exactly the frozen §7(A)-(T)
// decisions using only `oqiApi.commandCenter()` and
// `oqiApi.listFindings({status:"OPEN"})`, the two real, already-existing
// endpoints CDD-080 authorizes. Every number here is a direct pass-through
// or a pure client-side sort of real API fields -- no fabricated metric,
// no score, no trend, at any state.
export function EnterpriseUnderstandingPanel() {
  const [commandCenter, setCommandCenter] = useState<CommandCenterState>({
    status: "loading",
  });
  const [spotlight, setSpotlight] = useState<SpotlightState>({
    status: "loading",
  });

  useEffect(() => {
    const controller = new AbortController();

    oqiApi.commandCenter(controller.signal).then(
      (data) => setCommandCenter({ status: "loaded", data }),
      (caught) => {
        if (controller.signal.aborted) return;
        if (
          caught instanceof OqiApiError &&
          (caught.status === 401 || caught.status === 403)
        ) {
          setCommandCenter({ status: "unauthorized" });
          return;
        }
        setCommandCenter({
          status: "error",
          code: caught instanceof OqiApiError ? caught.code : "UNKNOWN_ERROR",
        });
      },
    );

    oqiApi.listFindings({ status: "OPEN", limit: 50 }, controller.signal).then(
      (response) => {
        // Generic selection only -- never a reference to any specific
        // finding ID. Under today's seeded demo data this may genuinely
        // surface the certified Country-of-Origin finding; the same
        // code surfaces whatever finding real data ranks highest under
        // different data, with zero change (CDD-080 §7-F).
        const sorted = [...response.items].sort(
          (a, b) =>
            (CRITICALITY_ORDER[b.highest_criticality ?? ""] ?? -1) -
            (CRITICALITY_ORDER[a.highest_criticality ?? ""] ?? -1),
        );
        setSpotlight({ status: "loaded", finding: sorted[0] ?? null });
      },
      (caught) => {
        if (controller.signal.aborted) return;
        if (
          caught instanceof OqiApiError &&
          (caught.status === 401 || caught.status === 403)
        ) {
          setSpotlight({ status: "unauthorized" });
          return;
        }
        setSpotlight({
          status: "error",
          code: caught instanceof OqiApiError ? caught.code : "UNKNOWN_ERROR",
        });
      },
    );

    return () => controller.abort();
  }, []);

  return (
    <div className="obs-eu">
      <section
        className="obs-intelligence-surface"
        aria-label="Enterprise understanding"
      >
        <div className="obs-eu-hero">
          <span className="eyebrow">Enterprise understanding</span>
          {renderHero(commandCenter)}
        </div>
        <div className="obs-eu-spotlight">
          <h2>Highest-priority open finding</h2>
          {renderSpotlight(spotlight)}
        </div>
      </section>

      {renderReliance(commandCenter)}
      {renderAttention(commandCenter)}
    </div>
  );
}

function renderHero(state: CommandCenterState) {
  if (state.status === "loading") {
    return (
      <EmptyState kind="loading" title="Loading enterprise understanding" />
    );
  }
  if (state.status === "unauthorized") {
    return (
      <EmptyState
        kind="not-authorized"
        title="Not authorized to view governed findings"
        message="This does not indicate anything about the underlying Reliance state."
      />
    );
  }
  if (state.status === "error") {
    return (
      <EmptyState
        kind="error"
        title="Governed findings are temporarily unavailable"
        message={`Backend unavailable (${state.code}). This is a technical failure, separate from the governed state.`}
      />
    );
  }
  return (
    <>
      <p className="obs-eu-hero-count">{state.data.open_findings_count}</p>
      <p className="obs-eu-hero-caption">
        Open governed findings across your enterprise data that require
        attention.
      </p>
    </>
  );
}

function renderSpotlight(state: SpotlightState) {
  if (state.status === "loading") {
    return (
      <EmptyState kind="loading" title="Loading the highest-priority finding" />
    );
  }
  if (state.status === "unauthorized") {
    return (
      <EmptyState
        kind="not-authorized"
        title="Not authorized to view this finding"
        message="This does not indicate anything about the underlying Reliance state."
      />
    );
  }
  if (state.status === "error") {
    return (
      <EmptyState
        kind="error"
        title="The highest-priority finding is temporarily unavailable"
        message={`Backend unavailable (${state.code}). This is a technical failure, separate from the governed state.`}
      />
    );
  }
  const { finding } = state;
  if (!finding) {
    return (
      <EmptyState
        kind="empty"
        title="No open findings"
        message="There is currently no open governed finding to spotlight."
      />
    );
  }
  return (
    <div className="obs-eu-spotlight-card obs-eu-spotlight-enter">
      <span className="obs-eu-spotlight-family">{finding.finding_family}</span>
      <h3>{finding.condition_label}</h3>
      <div className="obs-eu-spotlight-status">
        <span className="obs-eu-spotlight-status-item">
          <StatusIndicator status="conflict" />
          <span>Criticality — {finding.highest_criticality ?? "Unknown"}</span>
        </span>
        <span className="obs-eu-spotlight-status-item">
          <StatusIndicator status={relianceStatus(finding.reliance_state)} />
          <span>Reliance</span>
        </span>
      </div>
      <Link className="button" href={`/quality/findings/${finding.finding_id}`}>
        Open finding
      </Link>
    </div>
  );
}

function renderReliance(state: CommandCenterState) {
  const body = (() => {
    if (state.status === "loading") {
      return <EmptyState kind="loading" title="Loading Reliance state" />;
    }
    if (state.status === "unauthorized") {
      return (
        <EmptyState
          kind="not-authorized"
          title="Not authorized to view Reliance state"
          message="This does not indicate anything about the underlying Reliance state."
        />
      );
    }
    if (state.status === "error") {
      return (
        <EmptyState
          kind="error"
          title="Reliance state is temporarily unavailable"
          message={`Backend unavailable (${state.code}). This is a technical failure, separate from the governed state.`}
        />
      );
    }
    const cells: {
      key: string;
      label: string;
      count: number;
      status: ObservatoryStatus;
    }[] = [
      {
        key: "supported",
        label: "Reliance Supported",
        count: state.data.reliance_supported_count,
        status: "verified",
      },
      {
        key: "at-risk",
        label: "Reliance At Risk",
        count: state.data.reliance_at_risk_count,
        status: "conflict",
      },
      {
        key: "unknown",
        label: "Reliance Unknown",
        count: state.data.reliance_unknown_count,
        status: "unknown",
      },
    ];
    return (
      <>
        {cells.map((cell) => (
          <Link
            key={cell.key}
            className="panel"
            href="/quality"
            style={{ display: "block" }}
          >
            <StatusIndicator status={cell.status} />
            <p
              style={{
                fontSize: "1.75rem",
                fontWeight: 700,
                lineHeight: 1,
                margin: "0.35rem 0",
              }}
            >
              {cell.count}
            </p>
            <span className="eyebrow">{cell.label}</span>
          </Link>
        ))}
      </>
    );
  })();

  return (
    <div
      role="group"
      aria-label="Enterprise knowledge reliance"
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(11rem, 1fr))",
        gap: "1rem",
      }}
    >
      {body}
    </div>
  );
}

function renderAttention(state: CommandCenterState) {
  const body = (() => {
    if (state.status === "loading") {
      return (
        <EmptyState kind="loading" title="Loading governed attention state" />
      );
    }
    if (state.status === "unauthorized") {
      return (
        <EmptyState
          kind="not-authorized"
          title="Not authorized to view governed attention state"
          message="This does not indicate anything about the underlying Reliance state."
        />
      );
    }
    if (state.status === "error") {
      return (
        <EmptyState
          kind="error"
          title="Governed attention state is temporarily unavailable"
          message={`Backend unavailable (${state.code}). This is a technical failure, separate from the governed state.`}
        />
      );
    }
    const authorizations = state.data.pending_human_authorizations_count;
    const investigations = state.data.active_agent_investigations_count;
    return (
      <>
        <Link
          className="panel"
          href="/quality/findings"
          style={{ display: "block" }}
        >
          <StatusIndicator
            status={authorizations > 0 ? "attention" : "not-exercised"}
          />
          <p
            style={{
              fontSize: "1.75rem",
              fontWeight: 700,
              lineHeight: 1,
              margin: "0.35rem 0",
            }}
          >
            {authorizations}
          </p>
          <span className="eyebrow">Pending Human Authorization</span>
        </Link>
        <Link
          className="panel"
          href="/quality/findings"
          style={{ display: "block" }}
        >
          <StatusIndicator
            status={investigations > 0 ? "pending" : "not-invoked"}
          />
          <p
            style={{
              fontSize: "1.75rem",
              fontWeight: 700,
              lineHeight: 1,
              margin: "0.35rem 0",
            }}
          >
            {investigations}
          </p>
          <span className="eyebrow">Active Agent Investigations</span>
        </Link>
      </>
    );
  })();

  return (
    <div
      role="group"
      aria-label="Governed human and agent attention"
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(11rem, 1fr))",
        gap: "1rem",
      }}
    >
      {body}
    </div>
  );
}
