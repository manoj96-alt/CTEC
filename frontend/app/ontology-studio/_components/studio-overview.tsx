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
    <ol aria-label="Ontology Studio journey" className="obs-ontology-journey">
      {JOURNEY_STEPS.map((step, index) => (
        <li key={step}>
          {step}
          {index < JOURNEY_STEPS.length - 1 ? " →" : ""}
        </li>
      ))}
    </ol>
  );
}

// CDD-083 §5.1: the orientation region migrates from a light `.panel` to
// the frozen, rationed `.obs-intelligence-surface` (CDD-078 §3) -- the
// same dark-canvas treatment already shipped for Overview's hero/
// spotlight -- extending its designed use to a second, genuinely
// orientation-shaped surface ("what ontology am I looking at"). Every
// real field already rendered here is preserved verbatim; only its
// typographic/color treatment changes.
export function StudioOverview({
  ontology,
  connectorCount,
}: {
  ontology: OntologyDetail;
  connectorCount: number;
}) {
  return (
    <section className="obs-intelligence-surface obs-ontology-overview">
      <span className="obs-eu-eyebrow">Ontology</span>
      <h1 className="obs-ontology-title">{ontology.name}</h1>
      <JourneyIndicator />
      <p className="obs-ontology-description">{ontology.description}</p>
      <dl className="obs-ontology-stats">
        <div>
          <dt>Ontology ID</dt>
          <dd className="mono">{ontology.ontology_id}</dd>
        </div>
        <div>
          <dt>Version</dt>
          <dd>{ontology.version}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{ontology.status}</dd>
        </div>
        <div>
          <dt>Concepts</dt>
          <dd>{ontology.concepts.length}</dd>
        </div>
        <div>
          <dt>Relationships</dt>
          <dd>{ontology.relationships.length}</dd>
        </div>
        <div>
          <dt>Quality score</dt>
          <dd>{(ontology.quality.overall_score * 100).toFixed(0)}%</dd>
        </div>
        <div>
          <dt>Connected sources</dt>
          <dd>{connectorCount}</dd>
        </div>
        <div>
          <dt>Activation applications</dt>
          <dd>{ontology.activation_applications.join(", ")}</dd>
        </div>
      </dl>
    </section>
  );
}

export function connectorCount(connectors: Connector[]): number {
  return connectors.filter((c) => c.maturity === "Demo Connected").length;
}
