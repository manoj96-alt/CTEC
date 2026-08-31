import type { RemediationResponse } from "@/lib/oqi/contracts";

// CDD-045 §20/§48-49/§29 UI Truth Table -- the highest-stakes panel in the
// whole product. Recommendation, human authorization, and external
// remediation are always three visually and structurally distinct facts.
// "External remediation reported" never becomes "Resolved" here -- only a
// Finding transitioning to RESOLVED via the real deterministic evaluator
// (rendered on the parent Finding-detail shell) may ever say that.
export function RemediationPanel({
  remediation,
}: {
  remediation: RemediationResponse;
}) {
  const hasNothing =
    !remediation.candidate &&
    !remediation.recommendation &&
    !remediation.authorization &&
    !remediation.external_execution;

  if (hasNothing) {
    return (
      <div>
        <h3>Remediation</h3>
        <p>No remediation activity recorded for this Finding.</p>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <h3>Remediation</h3>

      {remediation.candidate ? (
        <div className="panel">
          <span className="eyebrow">Deterministic candidate</span>
          <h4 style={{ marginTop: "0.25rem" }}>
            {remediation.candidate.proposed_value}
          </h4>
          <p style={{ fontWeight: 700 }}>Candidate — not established truth</p>
        </div>
      ) : null}

      <div className="panel">
        <span className="eyebrow">Agent Recommendation</span>
        {remediation.recommendation ? (
          <>
            <h4 style={{ marginTop: "0.25rem" }}>
              {remediation.recommendation.recommendation_type}
            </h4>
            <p>{remediation.recommendation.rationale}</p>
          </>
        ) : (
          <p>No agent recommendation exists for this Finding.</p>
        )}
      </div>

      <div className="panel">
        <span className="eyebrow">Human Authorization</span>
        {remediation.authorization ? (
          <>
            <h4 style={{ marginTop: "0.25rem" }}>
              {remediation.authorization.decided_on
                ? `Authorized by ${remediation.authorization.principal} at ${new Date(remediation.authorization.decided_on).toLocaleString()}`
                : "Authorization pending decision"}
            </h4>
            <p>{remediation.authorization.instruction}</p>
            {remediation.authorization.is_stale ? (
              <p role="alert" style={{ fontWeight: 700 }}>
                Stale — this authorization no longer matches the current Finding
                state and cannot be used.
              </p>
            ) : null}
          </>
        ) : (
          <p>No human authorization exists for this Finding.</p>
        )}
      </div>

      <div className="panel">
        <span className="eyebrow">External Remediation</span>
        {remediation.external_execution ? (
          <>
            <p style={{ fontWeight: 700 }}>
              External remediation reported — awaiting fresh evidence
            </p>
            <p>
              Reported at{" "}
              {new Date(
                remediation.external_execution.reported_at,
              ).toLocaleString()}
            </p>
            <p style={{ color: "var(--muted)" }}>
              This does not by itself resolve the underlying quality condition.
              Only fresh source evidence and deterministic re-evaluation can do
              that.
            </p>
          </>
        ) : (
          <p>No external remediation has been reported for this Finding.</p>
        )}
      </div>
    </div>
  );
}
