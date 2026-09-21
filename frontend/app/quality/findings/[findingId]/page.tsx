"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { EmptyState } from "@/components/design-system/empty-state";
import { StatusIndicator } from "@/components/design-system/status-indicator";
import { accessToken } from "@/lib/auth/browser-session";
import { browserAuthConfig } from "@/lib/auth/config";
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
import { ConflictLens } from "./_components/conflict-lens";
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

const VALID_TAB_KEYS = new Set<string>(TABS.map((entry) => entry.key));

function isValidTab(value: string | null): value is Tab {
  return value !== null && VALID_TAB_KEYS.has(value);
}

// CDD-084 §30, AA row 9: the exact backend `UniquenessCandidateDetailResponse`
// shape (declared locally -- `@/lib/oqi/contracts` / `@/lib/oqi/api-client`
// are not authorized paths for this phase, so this page fetches its own
// endpoint directly, reusing the SAME auth/error mechanics
// `@/lib/oqi/api-client`'s own internal (unexported) `request<T>` helper
// already establishes -- never a new auth pathway).
type UniquenessCandidateMemberView = {
  entity_id: string;
  entity_name: string;
  impact_outcome: string;
};

type UniquenessCandidateDetailResponse = {
  finding_id: string;
  candidate_id: string;
  finding_status: string;
  finding_state_revision: number;
  member_a: UniquenessCandidateMemberView;
  member_b: UniquenessCandidateMemberView;
  matched_normalized_name: string;
  policy_id: string;
  policy_version: number;
  candidate_created_on: string;
  latest_adjudication_action: string | null;
  latest_adjudication_actor_id: string | null;
  latest_adjudication_rationale: string | null;
  latest_adjudication_decided_on: string | null;
};

async function fetchUniquenessCandidateDetail(
  findingId: string,
  signal?: AbortSignal,
): Promise<UniquenessCandidateDetailResponse> {
  const token = await accessToken();
  if (!token) throw new OqiApiError("AUTH_REQUIRED", 401);
  const response = await fetch(
    `${browserAuthConfig().apiOrigin}/api/v1/oqi/uniqueness-candidates/${findingId}`,
    {
      signal,
      cache: "no-store",
      credentials: "omit",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    },
  );
  if (!response.ok) {
    const parsed = await response.json().catch(() => null);
    const code =
      parsed && typeof parsed === "object" && "detail" in parsed
        ? ((parsed as { detail?: { code?: string } }).detail?.code ??
          `HTTP_${response.status}`)
        : `HTTP_${response.status}`;
    throw new OqiApiError(code, response.status);
  }
  return (await response.json()) as UniquenessCandidateDetailResponse;
}

// CDD-084 §7/§28/§30: candidate language throughout -- never "duplicate
// entity" as established fact. Confirmation is shown as governed human
// evidence only ("confirmed as a possible duplicate"), never as proof, and
// never paired with any merge/deactivate control (none exists in this
// product surface, CDD-084 §2 PO-2).
function UniquenessCandidatePanel({
  detail,
}: {
  detail: UniquenessCandidateDetailResponse;
}) {
  const adjudicationLabel =
    detail.latest_adjudication_action === "CONFIRM_DUPLICATE"
      ? "Steward confirmed as a possible duplicate — not yet resolved"
      : detail.latest_adjudication_action === "REJECT_NOT_DUPLICATE"
        ? "Steward determined these are not duplicates"
        : "Awaiting steward review";

  return (
    <div>
      <h3>Possible Duplicate Enterprise Entities</h3>
      <p role="status">
        Candidate — not established fact. Governed evidence placed these two
        entities together for steward review.
      </p>

      <div className="obs-evidence-comparison">
        <div className="obs-evidence-sources">
          {[detail.member_a, detail.member_b].map((member) => (
            <div key={member.entity_id} className="obs-evidence-source-card">
              <span className="obs-evidence-source-name">
                {member.entity_name}
              </span>
              <span className="obs-evidence-source-caption">
                Ontology impact: {member.impact_outcome}
              </span>
            </div>
          ))}
        </div>
      </div>

      <p className="obs-evidence-aggregate">
        Matched governed evidence: normalized name &quot;
        {detail.matched_normalized_name}&quot;
      </p>

      <div className="panel" style={{ marginTop: "1rem" }}>
        <span className="eyebrow">Steward Adjudication</span>
        <h4 style={{ marginTop: "0.25rem" }}>
          <StatusIndicator
            status={
              detail.latest_adjudication_action === "REJECT_NOT_DUPLICATE"
                ? "verified"
                : "unknown"
            }
          />{" "}
          {adjudicationLabel}
        </h4>
        {detail.latest_adjudication_rationale ? (
          <p style={{ color: "var(--muted)" }}>
            {detail.latest_adjudication_rationale}
          </p>
        ) : null}
      </div>
    </div>
  );
}

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
      uniquenessCandidate: UniquenessCandidateDetailResponse | null;
    }
  | { status: "not_found" }
  | { status: "unauthorized" }
  | { status: "error"; code: string };

// Next.js requires any component reading useSearchParams() to render inside
// a Suspense boundary (missing-suspense-with-csr-bailout) -- this is a
// render-boundary requirement only, mirroring findings/page.tsx's own
// existing precedent; it changes nothing about data-fetch or tab behavior,
// all of which live in FindingDetailPageContent below.
export default function FindingDetailPage() {
  return (
    <Suspense fallback={<EmptyState kind="loading" title="Loading Finding" />}>
      <FindingDetailPageContent />
    </Suspense>
  );
}

function FindingDetailPageContent() {
  const params = useParams<{ findingId: string }>();
  const findingId = params.findingId;
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialTab = searchParams.get("tab");
  const [tab, setTabState] = useState<Tab>(
    isValidTab(initialTab) ? initialTab : "evidence",
  );
  const [state, setState] = useState<LoadState>({ status: "loading" });

  // Navigation state only -- an invalid/missing ?tab= value safely falls
  // back to "evidence" above and never changes authorization or data-fetch
  // behavior; this only keeps the URL addressable for the currently
  // selected tab, using client-side routing (no full page reload).
  const setTab = useCallback(
    (next: Tab) => {
      setTabState(next);
      const query = new URLSearchParams(searchParams.toString());
      query.set("tab", next);
      router.replace(`/quality/findings/${findingId}?${query.toString()}`, {
        scroll: false,
      });
    },
    [findingId, router, searchParams],
  );

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
        async ([
          finding,
          evidence,
          impact,
          businessImpact,
          reliance,
          agent,
          remediation,
        ]) => {
          // CDD-084 §30: the pair-detail endpoint is fetched only for
          // Uniqueness Findings -- every other family's own request set
          // above is completely unchanged.
          const uniquenessCandidate =
            finding.finding_family === "UNIQUENESS"
              ? await fetchUniquenessCandidateDetail(findingId)
              : null;
          setState({
            status: "loaded",
            finding,
            evidence,
            impact,
            businessImpact,
            reliance,
            agent,
            remediation,
            uniquenessCandidate,
          });
        },
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

  return (
    <div className="max-w-5xl">
      <ConflictLens
        finding={finding}
        evidence={state.evidence}
        impact={state.impact}
        businessImpact={state.businessImpact}
        reliance={state.reliance}
      />

      {/* WOW-I3-A-R5 §7: six investigation perspectives, not workflow
          steps -- a flat underline-tab pattern (mirroring the already-
          shipped primary-nav active treatment) rather than a numbered
          stepper, so the navigation never implies the six execute in
          sequence or automatically. */}
      <nav aria-label="Finding investigation" className="obs-investigation-nav">
        {TABS.map((entry) => (
          <button
            key={entry.key}
            className="obs-investigation-tab"
            aria-current={tab === entry.key ? "page" : undefined}
            onClick={() => setTab(entry.key)}
          >
            {entry.label}
          </button>
        ))}
      </nav>

      <section className="panel">
        {tab === "evidence" &&
          (finding.finding_family === "UNIQUENESS" &&
          state.uniquenessCandidate ? (
            <UniquenessCandidatePanel detail={state.uniquenessCandidate} />
          ) : (
            <EvidencePanel
              evidence={state.evidence}
              findingFamily={finding.finding_family}
            />
          ))}
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
          <RemediationPanel remediation={state.remediation} onMutated={load} />
        )}
      </section>
    </div>
  );
}
