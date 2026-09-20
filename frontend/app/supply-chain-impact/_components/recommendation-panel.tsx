import type {
  CandidateOutcome,
  MaterialEvaluationResult,
} from "@/lib/supply-chain-impact/contracts";

function conditionLabel(value: boolean | null): string {
  if (value === true) return "Satisfied";
  if (value === false) return "Not satisfied";
  return "Unknown";
}

function conditionTone(value: boolean | null): string {
  if (value === true) return "obs-sci-condition-tag--pass";
  if (value === false) return "obs-sci-condition-tag--fail";
  return "obs-sci-condition-tag--unknown";
}

function evidenceBoolean(
  candidate: CandidateOutcome | undefined,
  predicate: string,
): boolean | null {
  const item = candidate?.evidence.find(
    (entry) => entry.predicate === predicate,
  );
  if (!item) return null;
  return item.value === "true";
}

// WOW-I4-B1-R3 (operator: "make the recommendation more explainable...
// inspect Gate F, use the actual governed conditions -- do not invent
// condition names"): the real Gate F four-condition mitigation policy,
// confirmed directly against `backend/app/integration/adapters/gate_f/
// drm.py` (CDD-015 §11) -- shown as five independently observable
// governed facts, because condition 4 ("qualified alternate with
// sufficient capacity") is itself gated on two separately distinguishable
// real facts (Gate F's own `GateFOutcomeReason` enum has distinct
// REJECTED_NOT_QUALIFIED / REJECTED_INSUFFICIENT_CAPACITY reasons for
// them). Every value read here is already present on `material`/
// `candidate.evidence` -- no threshold, comparison, or outcome is
// computed in this component; the backend's own `outcome`/`reason`/
// `narrative` below remain the sole authoritative conclusion, rendered
// exactly as before.
function GovernedConditions({
  material,
  candidate,
}: {
  material: MaterialEvaluationResult;
  candidate: CandidateOutcome | undefined;
}) {
  const conditions = [
    {
      label: "High-severity disruption",
      value: material.high_severity_disruption,
    },
    {
      label: "Single-source exposure",
      value: material.single_source_exposure,
    },
    {
      label: "Revenue exceeds materiality threshold",
      value: material.revenue_materiality,
    },
    {
      label: "Qualified alternate",
      value: evidenceBoolean(candidate, "qualification"),
    },
    {
      label: "Sufficient alternate capacity",
      value: evidenceBoolean(candidate, "capacity"),
    },
  ];
  return (
    <div className="obs-sci-conditions" aria-label="Governed conditions">
      <div className="obs-eu-eyebrow">Governed conditions</div>
      <ul>
        {conditions.map((condition) => (
          <li key={condition.label}>
            <span>{condition.label}</span>
            <span
              className={`status-tag obs-sci-condition-tag ${conditionTone(condition.value)}`}
            >
              {conditionLabel(condition.value)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

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
  material,
}: {
  candidate: CandidateOutcome | undefined;
  policyReference: string;
  policyVersion: string;
  material?: MaterialEvaluationResult;
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
        {material && (
          <GovernedConditions material={material} candidate={candidate} />
        )}
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
      {material && (
        <GovernedConditions material={material} candidate={candidate} />
      )}
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
