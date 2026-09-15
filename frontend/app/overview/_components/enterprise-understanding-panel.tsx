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

// WOW-I2-R1 §2: the real backend `condition_label` field is, for every
// finding family, a direct pass-through of the internal
// `quality_condition_id`/`business_condition_id` (confirmed by reading
// backend/app/application/oqi_product_experience_service.py's
// `list_findings` -- e.g. `condition_label=model1.quality_condition_id`)
// -- a technical identifier, not a human-authored title, despite its
// name. No separate human-readable title/name field exists anywhere in
// FindingSummary. This is the same real, already-shipped family-label
// mapping already used verbatim in the Findings page's own filter
// dropdown (frontend/app/quality/findings/page.tsx) -- reused here, not
// invented -- to give the spotlight a truthful primary heading, while
// `condition_label` itself is preserved exactly as returned and only
// demoted to a smaller, monospace identifier treatment below it.
const FINDING_FAMILY_LABEL: Record<string, string> = {
  OQI1: "Completeness / Validity",
  OQI2: "Cross-Source Consistency",
  OQI3: "Business Rules",
};

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
        <div className="obs-eu-story">
          <div className="obs-eu-hero">
            <span className="obs-eu-eyebrow">Enterprise understanding</span>
            {renderHero(commandCenter)}
          </div>
          <div className="obs-eu-spotlight">
            <span className="obs-eu-eyebrow">
              Highest-priority open finding
            </span>
            {renderSpotlight(spotlight)}
          </div>
        </div>
      </section>

      <div className="obs-eu-section">
        <span className="obs-eu-section-label">Reliance</span>
        {renderReliance(commandCenter)}
      </div>
      <div className="obs-eu-section">
        <span className="obs-eu-section-label">Governed attention</span>
        {renderAttention(commandCenter)}
      </div>
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
      <h3>
        {FINDING_FAMILY_LABEL[finding.finding_family] ?? finding.finding_family}
      </h3>
      <span className="obs-eu-spotlight-id">{finding.condition_label}</span>
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
            className={`panel obs-eu-reliance-cell obs-eu-reliance-cell--${cell.key}`}
            href="/quality"
          >
            <StatusIndicator status={cell.status} />
            <p className="obs-eu-reliance-count">{cell.count}</p>
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
      className="obs-eu-reliance-grid"
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
        <Link className="panel obs-eu-attention-cell" href="/quality/findings">
          <StatusIndicator
            status={authorizations > 0 ? "attention" : "not-exercised"}
          />
          <span className="obs-eu-attention-count">{authorizations}</span>
          <span className="obs-eu-attention-label">
            Pending Human Authorization
          </span>
        </Link>
        <Link className="panel obs-eu-attention-cell" href="/quality/findings">
          <StatusIndicator
            status={investigations > 0 ? "pending" : "not-invoked"}
          />
          <span className="obs-eu-attention-count">{investigations}</span>
          <span className="obs-eu-attention-label">
            Active Agent Investigations
          </span>
        </Link>
      </>
    );
  })();

  return (
    <div
      role="group"
      aria-label="Governed human and agent attention"
      className="obs-eu-attention-grid"
    >
      {body}
    </div>
  );
}
