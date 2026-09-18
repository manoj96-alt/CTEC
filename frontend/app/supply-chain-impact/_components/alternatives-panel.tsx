import type { CandidateOutcome } from "@/lib/supply-chain-impact/contracts";

// The API exposes only the candidate's entity id, not a human-readable
// name (CDD-016 §6, presentation limitation #1) -- this fallback label
// fabricates nothing about the candidate's identity beyond what the API
// already returned.
function candidateLabel(alternateSupplierEntityId: string | null): string {
  if (!alternateSupplierEntityId) return "No candidate";
  return `Alternate Supplier (…${alternateSupplierEntityId.slice(-8)})`;
}

function evidenceValue(
  candidate: CandidateOutcome,
  predicate: string,
): string | null {
  return (
    candidate.evidence.find((item) => item.predicate === predicate)?.value ??
    null
  );
}

// WOW-I4-B1-R1 (operator: "large mostly-empty Alternatives panel is
// unacceptable"): information density matched to the real amount of data
// -- the same four real fields (qualification/capacity/leadTimeDays/
// costUsd), tighter card, no score/ranking/winner. WOW-I4-B1-R3 (operator:
// "Alternatives looks like one database record"; provenance traced end to
// end, §3-4 of the governing prompt): the backend genuinely discovers
// candidates by querying the tenant graph for every "Alternate Supplier"-
// typed entity (not a hardcoded id lookup) and evaluates each
// independently -- real capability, just never exercised with more than
// one seeded candidate today. No ranking/scoring logic exists anywhere in
// Gate F, so "ALTERNATIVE UNDER EVALUATION" (the neutral framing the
// governing prompt itself proposes) is what the product can truthfully
// say -- never "best"/"optimal"/"discovered"/"top candidate".
export function AlternativesPanel({
  candidates,
}: {
  candidates: CandidateOutcome[];
}) {
  return (
    <section className="panel" aria-label="Alternatives">
      <div className="eyebrow">Alternatives</div>
      <h2>What alternatives exist?</h2>
      {candidates.length === 0 ? (
        <p className="obs-sci-empty-evidence">
          No candidate alternate suppliers were evaluated.
        </p>
      ) : (
        <ul className="obs-sci-alt-list">
          {candidates.map((candidate, index) => (
            <li
              key={candidate.alternate_supplier_entity_id ?? index}
              className="obs-sci-alt-card"
            >
              <div className="obs-sci-alt-eyebrow">
                Alternative under evaluation
              </div>
              <strong className="obs-sci-alt-name">
                {candidateLabel(candidate.alternate_supplier_entity_id)}
              </strong>
              <dl className="obs-sci-alt-grid">
                <div>
                  <dt>Qualification</dt>
                  <dd>
                    {evidenceValue(candidate, "qualification") ?? "Unknown"}
                  </dd>
                </div>
                <div>
                  <dt>Capacity</dt>
                  <dd>{evidenceValue(candidate, "capacity") ?? "Unknown"}</dd>
                </div>
                <div>
                  <dt>Lead time</dt>
                  <dd>
                    {evidenceValue(candidate, "leadTimeDays")
                      ? `${evidenceValue(candidate, "leadTimeDays")} days`
                      : "Not provided"}
                  </dd>
                </div>
                <div>
                  <dt>Cost context</dt>
                  <dd>
                    {evidenceValue(candidate, "costUsd") ?? "Not provided"}
                  </dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      )}
      {candidates.length > 0 && (
        <p className="obs-sci-alt-note">
          These are the real, governed facts Gate F&rsquo;s four-condition
          mitigation policy evaluates for each candidate.
        </p>
      )}
    </section>
  );
}
