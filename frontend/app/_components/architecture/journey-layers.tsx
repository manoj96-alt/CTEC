const SAMPLE_FILES = [
  "suppliers.csv",
  "materials.csv",
  "products.csv",
  "facilities.csv",
  "supply_agreements.csv",
  "risk_events.csv",
  "revenue_exposure.csv",
] as const;

const STAGES = [
  {
    label: "Import Data",
    description:
      "The seven controlled sample CSV files are parsed into the demo's known dataset structure.",
    detail: null,
    showFileList: true,
  },
  {
    label: "Map Schema",
    description:
      "Technical fields are mapped to business concepts using predefined sample mappings for this demo.",
    detail:
      "Each sample mapping includes a predefined sample mapping confidence value shown for illustration — it is fixed demo metadata, not a dynamically calculated or inferred confidence score.",
    showFileList: false,
  },
  {
    label: "Explore Ontology",
    description: "Records are connected into the sample ontology shown below.",
    detail:
      "Constructing these relationships is what enables impact analysis — calculating which materials, products, facilities, and revenue are connected to a disruption. Impact analysis is a capability within this stage, not a separate stage.",
    showFileList: false,
  },
  {
    label: "Decision Flow",
    description:
      "Explicit, deterministic rules are evaluated against the resolved sample facts.",
    detail:
      "No AI, LLM, or autonomous agent makes this evaluation — the conditions and their outcomes are plain, inspectable logic.",
    showFileList: false,
  },
  {
    label: "Recommendation",
    description: "The demo proposes a recommendation for human review.",
    detail:
      "Approve or Reject records the reviewer's decision in the current demo session. No operational action is executed and no enterprise system is updated. Recommendation factors and rule conditions are traceable to sample source rows — a fixture filename and row index — which are demo fixture references, not persisted enterprise lineage or immutable evidence records.",
    showFileList: false,
  },
] as const;

export function JourneyLayers() {
  return (
    <section>
      <p className="eyebrow">The five-stage journey</p>
      <h2 style={{ marginTop: "0.25rem" }}>
        How a sample dataset becomes a recommendation
      </h2>
      <ol
        style={{
          margin: "1rem 0 0",
          paddingLeft: "1.4rem",
          display: "grid",
          gap: "1rem",
        }}
      >
        {STAGES.map((stage) => (
          <li key={stage.label} className="panel" style={{ margin: 0 }}>
            <p style={{ fontWeight: 700, marginBottom: "0.35rem" }}>
              {stage.label}
            </p>
            <p style={{ fontSize: "0.9rem" }}>{stage.description}</p>
            {stage.showFileList && (
              <div style={{ marginTop: "0.5rem" }}>
                <p
                  style={{
                    fontSize: "0.85rem",
                    color: "var(--muted)",
                    marginBottom: "0.35rem",
                  }}
                >
                  These are fixed demo fixtures, not live connectors or
                  enterprise data sources:
                </p>
                <ul
                  style={{
                    margin: 0,
                    paddingLeft: "1.2rem",
                    fontSize: "0.85rem",
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(9rem, 1fr))",
                    gap: "0.25rem",
                  }}
                >
                  {SAMPLE_FILES.map((file) => (
                    <li key={file}>
                      <code>{file}</code>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {stage.detail && (
              <p
                style={{
                  fontSize: "0.85rem",
                  color: "var(--muted)",
                  marginTop: "0.5rem",
                }}
              >
                {stage.detail}
              </p>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
