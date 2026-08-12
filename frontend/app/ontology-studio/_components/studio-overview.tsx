import type {
  OntologyDetail,
  Connector,
} from "@/lib/ontology-studio/contracts";

const JOURNEY_STEPS = [
  "Connect",
  "Discover",
  "Model",
  "Validate",
  "Publish",
  "Activate",
];

export function JourneyIndicator() {
  return (
    <ol
      aria-label="Ontology Studio journey"
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "0.5rem",
        listStyle: "none",
        padding: 0,
        marginTop: "0.75rem",
        fontSize: "0.8rem",
        color: "var(--muted)",
      }}
    >
      {JOURNEY_STEPS.map((step, index) => (
        <li key={step}>
          {step}
          {index < JOURNEY_STEPS.length - 1 ? " →" : ""}
        </li>
      ))}
    </ol>
  );
}

export function StudioOverview({
  ontology,
  connectorCount,
}: {
  ontology: OntologyDetail;
  connectorCount: number;
}) {
  return (
    <section className="panel">
      <p className="eyebrow">Ontology Studio</p>
      <h1 style={{ marginTop: "0.25rem" }}>{ontology.name}</h1>
      <JourneyIndicator />
      <p
        style={{
          color: "var(--muted)",
          marginTop: "0.75rem",
          maxWidth: "42rem",
        }}
      >
        {ontology.description}
      </p>
      <dl
        style={{
          marginTop: "1rem",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(10rem, 1fr))",
          gap: "0.75rem",
          fontSize: "0.85rem",
        }}
      >
        <div>
          <dt style={{ color: "var(--muted)" }}>Ontology ID</dt>
          <dd style={{ fontWeight: 700 }}>{ontology.ontology_id}</dd>
        </div>
        <div>
          <dt style={{ color: "var(--muted)" }}>Version</dt>
          <dd style={{ fontWeight: 700 }}>{ontology.version}</dd>
        </div>
        <div>
          <dt style={{ color: "var(--muted)" }}>Status</dt>
          <dd style={{ fontWeight: 700 }}>{ontology.status}</dd>
        </div>
        <div>
          <dt style={{ color: "var(--muted)" }}>Concepts</dt>
          <dd style={{ fontWeight: 700 }}>{ontology.concepts.length}</dd>
        </div>
        <div>
          <dt style={{ color: "var(--muted)" }}>Relationships</dt>
          <dd style={{ fontWeight: 700 }}>{ontology.relationships.length}</dd>
        </div>
        <div>
          <dt style={{ color: "var(--muted)" }}>Quality score</dt>
          <dd style={{ fontWeight: 700 }}>
            {(ontology.quality.overall_score * 100).toFixed(0)}%
          </dd>
        </div>
        <div>
          <dt style={{ color: "var(--muted)" }}>Connected sources</dt>
          <dd style={{ fontWeight: 700 }}>{connectorCount}</dd>
        </div>
        <div>
          <dt style={{ color: "var(--muted)" }}>Activation applications</dt>
          <dd style={{ fontWeight: 700 }}>
            {ontology.activation_applications.join(", ")}
          </dd>
        </div>
      </dl>
    </section>
  );
}

export function connectorCount(connectors: Connector[]): number {
  return connectors.filter((c) => c.maturity === "Demo Connected").length;
}
