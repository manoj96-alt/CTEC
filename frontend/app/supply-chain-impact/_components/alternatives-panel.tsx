import type { CandidateOutcome } from "@/lib/supply-chain-impact/contracts";

// The API exposes only the candidate's entity id, not a human-readable
// name (CDD-016 §6, presentation limitation #1) -- this fallback label
// fabricates nothing about the candidate's identity beyond what the API
// already returned.
function candidateLabel(alternateSupplierEntityId: string | null): string {
  if (!alternateSupplierEntityId) return "No candidate";
  return `Alternate Supplier (…${alternateSupplierEntityId.slice(-8)})`;
}

function evidenceValue(candidate: CandidateOutcome, predicate: string): string | null {
  return candidate.evidence.find((item) => item.predicate === predicate)?.value ?? null;
}

export function AlternativesPanel({ candidates }: { candidates: CandidateOutcome[] }) {
  return (
    <section className="panel" aria-label="Alternatives">
      <div className="eyebrow">Alternatives</div>
      <h2>What alternatives exist?</h2>
      {candidates.length === 0 ? (
        <p>No candidate alternate suppliers were evaluated.</p>
      ) : (
        <ul className="record-list">
          {candidates.map((candidate, index) => (
            <li key={candidate.alternate_supplier_entity_id ?? index}>
              <strong>{candidateLabel(candidate.alternate_supplier_entity_id)}</strong>
              <dl className="status-grid">
                <dt>Qualification</dt>
                <dd>{evidenceValue(candidate, "qualification") ?? "Unknown"}</dd>
                <dt>Capacity</dt>
                <dd>{evidenceValue(candidate, "capacity") ?? "Unknown"}</dd>
                <dt>Lead time</dt>
                <dd>
                  {evidenceValue(candidate, "leadTimeDays")
                    ? `${evidenceValue(candidate, "leadTimeDays")} days`
                    : "Not provided"}
                </dd>
                <dt>Cost context</dt>
                <dd>{evidenceValue(candidate, "costUsd") ?? "Not provided"}</dd>
              </dl>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
