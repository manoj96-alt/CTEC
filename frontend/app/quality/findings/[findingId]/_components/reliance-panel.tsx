import type { RelianceResponse } from "@/lib/oqi/contracts";

// CDD-045 §16/§40/§29 UI Truth Table: exact governed language per state,
// plus the deterministic reason-code list rendered verbatim -- this
// component never recomputes OQI6 logic, it only renders what the API
// already decided.
const STATE_COPY: Record<string, string> = {
  RELIANCE_SUPPORTED: "Reliance Supported",
  RELIANCE_AT_RISK: "Reliance At Risk",
  RELIANCE_UNKNOWN: "Reliance Unknown — insufficient evidence to assess",
};

const REASON_COPY: Record<string, string> = {
  OPEN_QUALITY_CONDITION: "An open quality condition affects this knowledge.",
  INSUFFICIENT_QUALITY_COVERAGE:
    "Insufficient quality coverage has been evaluated.",
  ONTOLOGY_IMPACT_UNKNOWN: "Ontology impact cannot currently be determined.",
  BUSINESS_DEPENDENCY_UNKNOWN:
    "No governed business dependency coverage is known.",
  CRITICALITY_UNKNOWN: "No governed criticality has been assigned.",
  REMEDIATION_PENDING:
    "Remediation has been reported but not yet re-evaluated.",
};

export function ReliancePanel({ reliance }: { reliance: RelianceResponse }) {
  return (
    <div>
      <h3>Explainable Reliance</h3>
      <p style={{ fontWeight: 700 }}>
        {STATE_COPY[reliance.state] ?? reliance.state}
      </p>

      {reliance.reason_codes.length > 0 ? (
        <ul>
          {reliance.reason_codes.map((code) => (
            <li key={code}>{REASON_COPY[code] ?? code}</li>
          ))}
        </ul>
      ) : null}

      {reliance.history.length > 0 ? (
        <details style={{ marginTop: "0.75rem" }}>
          <summary>Reliance history</summary>
          <ul>
            {reliance.history.map((entry, index) => (
              <li key={`${entry.state}-${entry.evaluated_at}-${index}`}>
                {STATE_COPY[entry.state] ?? entry.state} —{" "}
                {new Date(entry.evaluated_at).toLocaleString()}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}
