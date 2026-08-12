const MODULES = [
  {
    responsibility:
      "Parses the seven sample CSV files into the demo's known dataset structure.",
    file: "fixture-loader.ts",
  },
  {
    responsibility:
      "Checks the parsed dataset for duplicate identifiers and broken references.",
    file: "dataset-validation.ts",
  },
  {
    responsibility:
      "Resolves the sample scenario's connected facts from the dataset, or reports exactly which relationship is missing.",
    file: "scenario-facts.ts",
  },
  {
    responsibility: "Builds the sample ontology graph from the resolved facts.",
    file: "ontology-model.ts",
  },
  {
    responsibility:
      "Evaluates the deterministic decision rules against the resolved facts.",
    file: "decision-rules.ts",
  },
];

export function HowThisWorksDetails() {
  return (
    <details className="panel">
      <summary style={{ fontWeight: 700, cursor: "pointer" }}>
        How this demo works
      </summary>
      <p
        style={{
          fontSize: "0.85rem",
          color: "var(--muted)",
          marginTop: "0.75rem",
        }}
      >
        This page is understandable without this section. It&apos;s here for
        anyone curious about how each stage above is actually built.
      </p>
      <ul
        style={{
          margin: "0.75rem 0 0",
          paddingLeft: "1.2rem",
          fontSize: "0.85rem",
        }}
      >
        {MODULES.map((module) => (
          <li key={module.file} style={{ marginBottom: "0.5rem" }}>
            {module.responsibility}{" "}
            <code style={{ color: "var(--muted)" }}>{module.file}</code>
          </li>
        ))}
      </ul>
    </details>
  );
}
