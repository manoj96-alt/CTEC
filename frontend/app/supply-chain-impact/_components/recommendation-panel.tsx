import type { CandidateOutcome } from "@/lib/supply-chain-impact/contracts";

// Renders exactly the governed recommendation the backend produced --
// never recalculated, rewritten, or generated client-side (CDD-016 §16).
// WOW-I4-B1-R1 (operator: "must no longer look like a footer card, must
// become the culminating visual object"): stronger hero typography/
// spacing inside the shared `.obs-intelligence-surface` "Governed
// Decision" block in page.tsx -- still no outcome-dependent color (would
// risk conflating this deterministic-policy outcome with OQI's distinct
// governed-evidence-quality semantic).
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
      <div
        className="obs-sci-decision-block"
        aria-label="Noetva recommendation"
        role="status"
      >
        <div className="obs-eu-eyebrow">Noetva recommendation</div>
        <h2 className="obs-sci-decision-outcome">
          Insufficient governed evidence
        </h2>
        <p>
          Noetva cannot safely recommend an action because required governed
          evidence is unavailable. This is not a rejection -- it means Noetva
          does not guess.
        </p>
        <p className="obs-sci-policy-ref">
          Policy: {policyReference} v{policyVersion}
        </p>
      </div>
    );
  }
  return (
    <div className="obs-sci-decision-block" aria-label="Noetva recommendation">
      <div className="obs-eu-eyebrow">Noetva recommendation</div>
      <h2 className="obs-sci-decision-outcome">{candidate.outcome}</h2>
      {candidate.reason && <p>{candidate.reason}</p>}
      {candidate.narrative && <p>{candidate.narrative}</p>}
      {candidate.structured_reasons.length > 0 && (
        <div className="obs-sci-reasons">
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
          <strong>Policy confidence:</strong> {candidate.confidence}
        </p>
      )}
      <p className="obs-sci-policy-ref">
        Policy: {policyReference} v{policyVersion}
      </p>
    </div>
  );
}
