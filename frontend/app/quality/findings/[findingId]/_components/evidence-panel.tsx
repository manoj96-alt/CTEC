import { StatusIndicator } from "@/components/design-system/status-indicator";
import type { EvidenceResponse } from "@/lib/oqi/contracts";

// CDD-045 §11/§29 UI Truth Table -- the signature N-source experience.
// Every governed participant renders, including missing and dissenting
// ones; agreement is described as "N governed peers observed {value}",
// never as correctness. A candidate, if one exists, is always labeled
// "Candidate — not established truth" -- this exact wording is load-
// bearing and must never be shortened to imply correctness.
//
// CDD-081 §11: `finding_family` is passed down so an empty
// `participants` list can be described truthfully. OQI2 is the only
// family that populates multi-source comparison (backend
// oqi_product_experience_service.py `get_evidence()`) -- OQI1/OQI3
// legitimately never do, by design (Classification D), so their empty
// list must never render the same "no evidence" wording a genuinely
// empty OQI2 case would.
export function EvidencePanel({
  evidence,
  findingFamily,
}: {
  evidence: EvidenceResponse;
  findingFamily?: string;
}) {
  const known = evidence.participants.filter(
    (p) => !p.is_missing && p.observed_value !== null,
  );
  const valueCounts = new Map<string, number>();
  for (const p of known) {
    if (p.observed_value) {
      valueCounts.set(
        p.observed_value,
        (valueCounts.get(p.observed_value) ?? 0) + 1,
      );
    }
  }

  return (
    <div>
      <h3>Source Evidence</h3>

      {evidence.participants.length === 0 ? (
        <p role="status">
          {findingFamily === "OQI2"
            ? "No source evidence has been recorded for this Finding."
            : "This finding type does not compare multiple governed sources."}
        </p>
      ) : (
        <div className="obs-evidence-rail">
          {evidence.participants.map((participant) => (
            <div key={participant.source_system} className="obs-evidence-row">
              <span className="obs-evidence-source">
                {participant.source_system}
              </span>
              <span className="obs-evidence-value">
                {participant.is_missing ? (
                  <span className="obs-evidence-missing">
                    <StatusIndicator status="unknown" />
                    <span>Missing</span>
                  </span>
                ) : (
                  participant.observed_value
                )}
              </span>
              <span className="obs-evidence-context">
                {participant.is_authoritative ? (
                  <span>Governed authoritative source</span>
                ) : null}
                {participant.is_conflicting ? (
                  <span className="obs-evidence-conflict">
                    <StatusIndicator status="conflict" />
                    <span>Conflicting</span>
                  </span>
                ) : null}
              </span>
            </div>
          ))}
        </div>
      )}

      {[...valueCounts.entries()].map(([value, count]) => (
        <p key={value} style={{ color: "var(--muted)" }}>
          {count} governed peer{count === 1 ? "" : "s"} observed {value}
        </p>
      ))}

      {evidence.candidate ? (
        <div className="panel" style={{ marginTop: "1rem" }}>
          <span className="eyebrow">Remediation candidate</span>
          <h4 style={{ marginTop: "0.25rem" }}>
            {evidence.candidate.proposed_value}
          </h4>
          <p style={{ color: "var(--muted)" }}>
            Basis: {evidence.candidate.supporting_participant_count} governed
            peer
            {evidence.candidate.supporting_participant_count === 1
              ? ""
              : "s"}{" "}
            agree
          </p>
          <p style={{ fontWeight: 700 }}>Candidate — not established truth</p>
        </div>
      ) : null}
    </div>
  );
}
