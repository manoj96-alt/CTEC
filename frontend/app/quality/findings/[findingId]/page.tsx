"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { EmptyState } from "@/components/design-system/empty-state";
import { PageHeader } from "@/components/design-system/page-header";
import { OqiApiError, oqiApi } from "@/lib/oqi/api-client";
import type {
  AgentInvestigationResponse,
  BusinessImpactResponse,
  EvidenceResponse,
  FindingDetailResponse,
  OntologyImpactResponse,
  RelianceResponse,
  RemediationResponse,
} from "@/lib/oqi/contracts";
import { AgentInvestigationPanel } from "./_components/agent-investigation-panel";
import { BusinessImpactPanel } from "./_components/business-impact-panel";
import { EvidencePanel } from "./_components/evidence-panel";
import { OntologyImpactPanel } from "./_components/ontology-impact-panel";
import { ReliancePanel } from "./_components/reliance-panel";
import { RemediationPanel } from "./_components/remediation-panel";

// CDD-045 §17/§28-29 -- the core investigation workspace. The chain is
// visible top to bottom: Finding -> Evidence -> Ontology Impact ->
// Business Impact -> Explainable Reliance -> Agent Investigation ->
// Remediation. Finding.status is the ONLY thing that may ever say
// "Resolved" (CDD-045 §29 UI Truth Table); external remediation being
// reported never does, no matter what tab it appears on.
type Tab =
  | "evidence"
  | "ontology-impact"
  | "business-impact"
  | "reliance"
  | "agent-investigation"
  | "remediation";

const TABS: { key: Tab; label: string }[] = [
  { key: "evidence", label: "Evidence" },
  { key: "ontology-impact", label: "Ontology Impact" },
  { key: "business-impact", label: "Business Impact" },
  { key: "reliance", label: "Explainable Reliance" },
  { key: "agent-investigation", label: "Agent Investigation" },
  { key: "remediation", label: "Remediation" },
];

type LoadState =
  | { status: "loading" }
  | {
      status: "loaded";
      finding: FindingDetailResponse;
      evidence: EvidenceResponse;
      impact: OntologyImpactResponse;
      businessImpact: BusinessImpactResponse;
      reliance: RelianceResponse;
      agent: AgentInvestigationResponse;
      remediation: RemediationResponse;
    }
  | { status: "not_found" }
  | { status: "unauthorized" }
  | { status: "error"; code: string };

export default function FindingDetailPage() {
  const params = useParams<{ findingId: string }>();
  const findingId = params.findingId;
  const [tab, setTab] = useState<Tab>("evidence");
  const [state, setState] = useState<LoadState>({ status: "loading" });

  const load = useCallback(() => {
    setState({ status: "loading" });
    Promise.all([
      oqiApi.findingDetail(findingId),
      oqiApi.evidence(findingId),
      oqiApi.ontologyImpact(findingId),
      oqiApi.businessImpact(findingId),
      oqiApi.reliance(findingId),
      oqiApi.agentInvestigation(findingId),
      oqiApi.remediation(findingId),
    ])
      .then(
        ([
          finding,
          evidence,
          impact,
          businessImpact,
          reliance,
          agent,
          remediation,
        ]) =>
          setState({
            status: "loaded",
            finding,
            evidence,
            impact,
            businessImpact,
            reliance,
            agent,
            remediation,
          }),
      )
      .catch((caught) => {
        if (caught instanceof OqiApiError) {
          if (caught.status === 404) {
            setState({ status: "not_found" });
            return;
          }
          if (caught.status === 401 || caught.status === 403) {
            setState({ status: "unauthorized" });
            return;
          }
          setState({ status: "error", code: caught.code });
          return;
        }
        setState({ status: "error", code: "UNKNOWN_ERROR" });
      });
  }, [findingId]);

  useEffect(() => {
    // Defer past this effect's own synchronous execution: load() itself sets
    // state, and calling it synchronously here would trigger a same-commit
    // re-render (react-hooks/set-state-in-effect). Queuing it as a microtask
    // keeps identical fetch/route behavior while letting this effect's own
    // commit finish first.
    queueMicrotask(() => load());
  }, [load]);

  if (state.status === "loading") {
    return <EmptyState kind="loading" title="Loading Finding" />;
  }
  if (state.status === "not_found") {
    return <EmptyState kind="empty" title="Finding not found" />;
  }
  if (state.status === "unauthorized") {
    return (
      <EmptyState
        kind="error"
        title="Not authorized to view this Finding"
        message="This does not indicate anything about the underlying quality state."
      />
    );
  }
  if (state.status === "error") {
    return (
      <EmptyState
        kind="error"
        title="Finding is temporarily unavailable"
        message={`Backend unavailable (${state.code}).`}
      />
    );
  }

  const { finding } = state;
  const isResolved = finding.status === "RESOLVED";

  return (
    <div className="max-w-5xl">
      <PageHeader
        eyebrow={finding.finding_family}
        title={finding.condition_label}
        description={
          isResolved
            ? `Resolved — confirmed by fresh evidence and re-evaluation on ${new Date(finding.last_seen_at).toLocaleString()}`
            : `Status: ${finding.status}`
        }
      />

      <nav
        aria-label="Finding investigation"
        style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}
      >
        {TABS.map((entry) => (
          <button
            key={entry.key}
            className="button"
            aria-current={tab === entry.key ? "page" : undefined}
            onClick={() => setTab(entry.key)}
          >
            {entry.label}
          </button>
        ))}
      </nav>

      <section className="panel">
        {tab === "evidence" && <EvidencePanel evidence={state.evidence} />}
        {tab === "ontology-impact" && (
          <OntologyImpactPanel impact={state.impact} />
        )}
        {tab === "business-impact" && (
          <BusinessImpactPanel impact={state.businessImpact} />
        )}
        {tab === "reliance" && <ReliancePanel reliance={state.reliance} />}
        {tab === "agent-investigation" && (
          <AgentInvestigationPanel investigation={state.agent} />
        )}
        {tab === "remediation" && (
          <RemediationPanel remediation={state.remediation} />
        )}
      </section>
    </div>
  );
}
