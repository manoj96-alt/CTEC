const IMPLEMENTED = [
  "Parsing the seven controlled sample CSV files into the demo's known dataset structure",
  "Duplicate identifier and broken reference detection within the sample dataset",
  "Constructing the sample ontology from resolved sample facts",
  "Calculating impact (revenue exposure, affected counts) from the sample ontology",
  "Evaluating explicit, deterministic decision rules",
  "Recording an Approve or Reject decision in the current demo session",
];

const ARCHITECTURAL_DIRECTION = [
  "Applying this same layered approach to an organization's own data",
  "Extending the ontology and decision rules beyond a single sample scenario",
];

const NOT_IMPLEMENTED = [
  "Live enterprise connectors",
  "Persistent decisions",
  "Operational execution",
  "Production evidence storage",
  "Multi-scenario ontology reasoning",
  "AI, LLM, or agent decision-making",
  "Dynamically calculated confidence",
  "Enterprise authentication or authorization",
];

function ScopeColumn({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="panel" style={{ margin: 0 }}>
      <p style={{ fontWeight: 700, marginBottom: "0.5rem" }}>{title}</p>
      <ul style={{ margin: 0, paddingLeft: "1.2rem", fontSize: "0.85rem" }}>
        {items.map((item) => (
          <li key={item} style={{ marginBottom: "0.35rem" }}>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ScopeComparison() {
  return (
    <section>
      <p className="eyebrow">Scope</p>
      <h2 style={{ marginTop: "0.25rem" }}>What this demo is and isn&apos;t</h2>
      <p
        style={{ color: "var(--muted)", fontSize: "0.9rem", maxWidth: "42rem" }}
      >
        &quot;Architectural direction&quot; describes where this approach could
        go — it is not already available in this demo.
      </p>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(14rem, 1fr))",
          gap: "1rem",
          marginTop: "1rem",
        }}
      >
        <ScopeColumn title="Implemented in this demo" items={IMPLEMENTED} />
        <ScopeColumn
          title="Architectural direction"
          items={ARCHITECTURAL_DIRECTION}
        />
        <ScopeColumn title="Not implemented" items={NOT_IMPLEMENTED} />
      </div>
    </section>
  );
}
