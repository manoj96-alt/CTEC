import type { CandidateOutcome } from "@/lib/supply-chain-impact/contracts";

// Renders exactly the governed recommendation the backend produced --
// never recalculated, rewritten, or generated client-side (CDD-016 §16).
export function RecommendationPanel({
  candidate,
  policyReference,
  policyVersion,
}: {
  candidate: CandidateOutcome | undefined;
  policyReference: string;
  policyVersion: string;
}) {
  if (!candidate || candidate.outcome === null) {
    return (
      <section className="panel" aria-label="CTEC recommendation" role="status">
        <div className="eyebrow">CTEC recommendation</div>
        <h2>Insufficient governed evidence</h2>
        <p>
          CTEC cannot safely recommend an action because required governed
          evidence is unavailable. This is not a rejection -- it means CTEC does
          not guess.
        </p>
        <p className="eyebrow" style={{ marginTop: "0.5rem" }}>
          Policy: {policyReference} v{policyVersion}
        </p>
      </section>
    );
  }
  return (
    <section className="panel recommendation" aria-label="CTEC recommendation">
      <div className="eyebrow">CTEC recommendation</div>
      <h2>{candidate.outcome}</h2>
      {candidate.reason && <p>{candidate.reason}</p>}
      {candidate.narrative && <p>{candidate.narrative}</p>}
      {candidate.structured_reasons.length > 0 && (
        <div className="conditions">
          <h3>Structured reasons</h3>
          <ul>
            {candidate.structured_reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      )}
      {candidate.confidence && (
        <p className="standing">
          <strong>Confidence:</strong> {candidate.confidence}
        </p>
      )}
      <p className="eyebrow" style={{ marginTop: "0.5rem" }}>
        Policy: {policyReference} v{policyVersion}
      </p>
    </section>
  );
}
