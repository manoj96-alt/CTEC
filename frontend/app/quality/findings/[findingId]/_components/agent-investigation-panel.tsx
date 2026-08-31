import type { AgentInvestigationResponse } from "@/lib/oqi/contracts";

// CDD-045 §18/§43/§29 UI Truth Table: specialist assessments render side by
// side and are never collapsed into a fabricated consensus -- disagreement
// is a feature of explainability, not a defect (CDD-045 §61). The
// recommendation's basis (specialist-supported vs. synthesizer-only) comes
// directly from the backend's own field -- never inferred from
// recommendation text.
export function AgentInvestigationPanel({
  investigation,
}: {
  investigation: AgentInvestigationResponse;
}) {
  if (investigation.specialists.length === 0 && investigation.recommendation === null) {
    return (
      <div>
        <h3>Agent Investigation</h3>
        <p role="status">Agent investigation unavailable.</p>
      </div>
    );
  }

  return (
    <div>
      <h3>Agent Investigation</h3>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(14rem, 1fr))",
          gap: "0.75rem",
        }}
      >
        {investigation.specialists.map((specialist) => (
          <div key={specialist.role_id} className="panel">
            <span className="eyebrow">Specialist Assessment</span>
            <h4 style={{ marginTop: "0.25rem" }}>{specialist.role_id}</h4>
            <p>{specialist.result_state}</p>
            {specialist.assessment_text ? <p>{specialist.assessment_text}</p> : null}
          </div>
        ))}
      </div>

      {investigation.recommendation ? (
        <div className="panel" style={{ marginTop: "1rem" }}>
          <span className="eyebrow">Recommendation</span>
          <h4 style={{ marginTop: "0.25rem" }}>{investigation.recommendation.recommendation_type}</h4>
          <p>{investigation.recommendation.rationale}</p>
          <p style={{ fontWeight: 700 }}>
            {investigation.recommendation.basis === "SYNTHESIZER_ONLY"
              ? "Specialist assessments unavailable — synthesizer reasoning only"
              : "Based on specialist assessments"}
          </p>
        </div>
      ) : null}
    </div>
  );
}
