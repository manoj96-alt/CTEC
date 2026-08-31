import type { BusinessImpactResponse } from "@/lib/oqi/contracts";

// CDD-045 §13/§34/§29 UI Truth Table: criticality is a property of a
// BusinessDependency, never the entity -- so every dependency renders as
// its own card, never collapsed to "the" criticality. UNKNOWN and
// NO_KNOWN states keep their narrow, exact governed wording.
export function BusinessImpactPanel({ impact }: { impact: BusinessImpactResponse }) {
  if (impact.outcome === "BUSINESS_IMPACT_UNKNOWN") {
    return (
      <div>
        <h3>Business Impact</h3>
        <p role="status">
          Business impact cannot currently be determined from available governed evidence.
        </p>
      </div>
    );
  }

  if (impact.outcome === "NO_KNOWN_BUSINESS_IMPACT") {
    return (
      <div>
        <h3>Business Impact</h3>
        <p>No known business impact.</p>
      </div>
    );
  }

  return (
    <div>
      <h3>Business Impact</h3>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(12rem, 1fr))",
          gap: "0.75rem",
        }}
      >
        {impact.dependencies.map((dependency) => (
          <div
            key={`${dependency.business_process_name}-${dependency.business_dependency_version}`}
            className="panel"
          >
            <span className="eyebrow">{dependency.business_process_name}</span>
            <h4 style={{ marginTop: "0.25rem" }}>{dependency.criticality ?? "Criticality Unknown"}</h4>
          </div>
        ))}
      </div>
    </div>
  );
}
