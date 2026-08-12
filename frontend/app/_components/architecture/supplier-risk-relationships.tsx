import { sampleRelationships } from "./sample-relationships";

export function SupplierRiskRelationships() {
  return (
    <section className="panel">
      <p className="eyebrow">Sample Supplier Risk Relationships</p>
      <p style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
        These are the relationships supported by the current sample ontology
        used in the Supplier Risk demo. This is not a universal ontology, a
        comprehensive enterprise model, or an automatically discovered semantic
        graph.
      </p>
      <ul
        style={{
          margin: "0.75rem 0 0",
          paddingLeft: "1.2rem",
          fontSize: "0.9rem",
        }}
      >
        {sampleRelationships.map((relationship) => (
          <li
            key={`${relationship.source}-${relationship.label}-${relationship.target}`}
          >
            {relationship.source} —{relationship.label}→ {relationship.target}
          </li>
        ))}
      </ul>
    </section>
  );
}
