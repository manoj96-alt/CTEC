import type { EvidenceResponse } from "@/lib/oqi/contracts";

// CDD-045 §11/§29 UI Truth Table -- the signature N-source experience.
// Every governed participant renders, including missing and dissenting
// ones; agreement is described as "N governed peers observed {value}",
// never as correctness. A candidate, if one exists, is always labeled
// "Candidate — not established truth" -- this exact wording is load-
// bearing and must never be shortened to imply correctness.
export function EvidencePanel({ evidence }: { evidence: EvidenceResponse }) {
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
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left" }}>Source</th>
            <th style={{ textAlign: "left" }}>Observed value</th>
            <th style={{ textAlign: "left" }}>Context</th>
          </tr>
        </thead>
        <tbody>
          {evidence.participants.map((participant) => (
            <tr key={participant.source_system}>
              <td>{participant.source_system}</td>
              <td>
                {participant.is_missing
                  ? "Missing"
                  : participant.observed_value}
              </td>
              <td>
                {participant.is_authoritative ? (
                  <span>Governed authoritative source</span>
                ) : null}
                {participant.is_conflicting ? (
                  <span style={{ marginLeft: "0.5rem" }}>Conflicting</span>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

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
