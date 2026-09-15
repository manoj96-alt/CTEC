import {
  StatusIndicator,
  type ObservatoryStatus,
} from "@/components/design-system/status-indicator";
import type {
  BusinessImpactResponse,
  EvidenceResponse,
  FindingDetailResponse,
  OntologyImpactResponse,
  RelianceResponse,
} from "@/lib/oqi/contracts";

// CDD-081 §12: composed entirely from data the finding-detail shell has
// already fetched -- zero new API calls. Replaces the previous raw
// PageHeader(eyebrow=finding_family, title=condition_label) usage, which
// surfaced a technical identifier as the page's primary heading with no
// governed-attention context at all (WOW-I2-R1 operator observation).
//
// The real backend `condition_label` field is, for every finding family,
// a direct pass-through of the internal `quality_condition_id`/
// `business_condition_id` (backend/app/application/
// oqi_product_experience_service.py `list_findings`) -- a technical
// identifier, not a human-authored title. This reuses the same real
// family-label mapping already shipped in the Findings filter dropdown
// and the Overview spotlight (not invented) as the truthful primary
// heading, demoting `condition_label` to a monospace identifier line
// below it -- preserved verbatim, never removed. CDD-081 §10 discovery
// additionally confirmed two more real top-level family values beyond
// OQI1/OQI2/OQI3 -- INTEGRITY and TIMELINESS -- mapped here to their own
// already-real filter-option text, never a fabricated label.
const FINDING_FAMILY_LABEL: Record<string, string> = {
  OQI1: "Completeness / Validity",
  OQI2: "Cross-Source Consistency",
  OQI3: "Business Rules",
  INTEGRITY: "Integrity",
  TIMELINESS: "Timeliness",
};

// Mirrors the backend's own closed, four-value Criticality ordering
// (backend/app/domain/oqi_business_impact/dependency.py,
// `criticality_sort_key`) -- never reinvented, never carries
// quantitative/monetary meaning. Used only to surface the highest real
// per-dependency criticality already present in `businessImpact`.
const CRITICALITY_ORDER: Record<string, number> = {
  LOW: 0,
  MEDIUM: 1,
  HIGH: 2,
  CRITICAL: 3,
};

const RELIANCE_LABEL: Record<string, string> = {
  RELIANCE_SUPPORTED: "Reliance Supported",
  RELIANCE_AT_RISK: "Reliance At Risk",
  RELIANCE_UNKNOWN: "Reliance Unknown",
};

function relianceStatus(state: string): ObservatoryStatus {
  if (state === "RELIANCE_SUPPORTED") return "verified";
  if (state === "RELIANCE_AT_RISK") return "conflict";
  return "unknown";
}

export function ConflictLens({
  finding,
  evidence,
  impact,
  businessImpact,
  reliance,
}: {
  finding: FindingDetailResponse;
  evidence: EvidenceResponse;
  impact: OntologyImpactResponse;
  businessImpact: BusinessImpactResponse;
  reliance: RelianceResponse;
}) {
  const isResolved = finding.status === "RESOLVED";

  // OQI1/OQI3 findings legitimately never populate `participants` (a
  // different, real evidence representation -- CDD-081 §11
  // Classification D), so an empty list here is never described the same
  // way a genuinely empty OQI2 comparison would be.
  const hasConflictingEvidence = evidence.participants.some(
    (p) => p.is_conflicting,
  );
  const evidenceStatus: ObservatoryStatus =
    evidence.participants.length === 0
      ? "unknown"
      : hasConflictingEvidence
        ? "conflict"
        : "verified";
  const evidenceText =
    evidence.participants.length === 0
      ? finding.finding_family === "OQI2"
        ? "No source evidence recorded"
        : "Does not compare multiple sources"
      : hasConflictingEvidence
        ? "Sources disagree"
        : "Sources agree";

  const impactStatus: ObservatoryStatus =
    impact.outcome === "IMPACT_UNKNOWN"
      ? "unknown"
      : impact.outcome === "NO_IMPACT"
        ? "verified"
        : "conflict";
  const impactText =
    impact.outcome === "IMPACT_UNKNOWN"
      ? "Ontology impact unknown"
      : impact.outcome === "NO_IMPACT"
        ? "No ontology impact"
        : `Ontology impact — ${impact.direct_entity_type ?? "Entity"}`;

  const highestCriticality = businessImpact.dependencies
    .map((dependency) => dependency.criticality)
    .filter((criticality): criticality is string => criticality !== null)
    .sort(
      (a, b) => (CRITICALITY_ORDER[b] ?? -1) - (CRITICALITY_ORDER[a] ?? -1),
    )[0];
  const businessStatus: ObservatoryStatus =
    businessImpact.outcome === "BUSINESS_IMPACT_UNKNOWN"
      ? "unknown"
      : businessImpact.outcome === "NO_KNOWN_BUSINESS_IMPACT"
        ? "verified"
        : "conflict";
  const businessText =
    businessImpact.outcome === "BUSINESS_IMPACT_UNKNOWN"
      ? "Business impact unknown"
      : businessImpact.outcome === "NO_KNOWN_BUSINESS_IMPACT"
        ? "No known business impact"
        : `Business impact — ${highestCriticality ?? "Criticality Unknown"}`;

  return (
    <div className="obs-cl">
      <span className="obs-eu-eyebrow">Finding</span>
      <h1 className="obs-cl-title">
        {FINDING_FAMILY_LABEL[finding.finding_family] ?? finding.finding_family}
      </h1>
      <span className="obs-cl-id">{finding.condition_label}</span>
      <p className="obs-cl-status-line">
        {isResolved
          ? `Resolved — confirmed by fresh evidence and re-evaluation on ${new Date(finding.last_seen_at).toLocaleString()}`
          : `Status: ${finding.status}`}
      </p>
      <div className="obs-cl-signals">
        <span className="obs-cl-signal">
          <StatusIndicator status={evidenceStatus} />
          <span>{evidenceText}</span>
        </span>
        <span className="obs-cl-signal">
          <StatusIndicator status={impactStatus} />
          <span>{impactText}</span>
        </span>
        <span className="obs-cl-signal">
          <StatusIndicator status={businessStatus} />
          <span>{businessText}</span>
        </span>
        <span className="obs-cl-signal">
          <StatusIndicator status={relianceStatus(reliance.state)} />
          <span>{RELIANCE_LABEL[reliance.state] ?? reliance.state}</span>
        </span>
      </div>
    </div>
  );
}
