"use client";

import type {
  OntologyImpactResponse,
  PropagatedImpact,
  PropagatedImpactHop,
} from "@/lib/oqi/contracts";

// CDD-045 §12/§15/§29 + CDD-092 §17: this panel answers "what governed
// ontology knowledge is exposed by this Finding?", nothing more. Entity-level
// only (no attribute-level lineage, CDD-042 §4.7). Propagation is EXPOSURE
// through governed dependencies -- never causation, criticality, or a truth
// claim. IMPACT_UNKNOWN gets its own explicit state; absence of a propagated
// path is never presented as "not impacted".

const MAX_RETAINED_PATHS = 3;

function relationshipLabel(name: string): string {
  return name.replace(/([a-z])([A-Z])/g, "$1 $2").toLowerCase();
}

function hopSentence(hop: PropagatedImpactHop): string {
  return hop.direction === "REVERSE"
    ? `${hop.from_entity_name} ← ${relationshipLabel(hop.relationship_type_name)} — ${hop.to_entity_name}`
    : `${hop.from_entity_name} — ${relationshipLabel(hop.relationship_type_name)} → ${hop.to_entity_name}`;
}

function ImpactChain({ path }: { path: PropagatedImpactHop[] }) {
  if (path.length === 0) return null;
  return (
    <ol className="impact-chain" aria-label="Governed dependency path">
      <li>
        <strong>{path[0].from_entity_name}</strong>
      </li>
      {path.map((hop) => (
        <li key={`${hop.relationship_instance_id}-${hop.to_entity_id}`}>
          <span className="muted">
            ↓ {relationshipLabel(hop.relationship_type_name)}
            {hop.direction === "REVERSE" ? " (reverse)" : ""}
          </span>
          <br />
          <strong>{hop.to_entity_name}</strong>
        </li>
      ))}
    </ol>
  );
}

function primaryExposure(
  impacts: PropagatedImpact[],
): PropagatedImpact | undefined {
  // The deepest exposed element (server order breaks ties deterministically).
  return impacts.reduce<PropagatedImpact | undefined>(
    (deepest, item) =>
      deepest === undefined || item.depth > deepest.depth ? item : deepest,
    undefined,
  );
}

export function OntologyImpactPanel({
  impact,
}: {
  impact: OntologyImpactResponse;
}) {
  if (impact.outcome === "IMPACT_UNKNOWN") {
    return (
      <div>
        <h3>Ontology Impact</h3>
        <p role="status">
          Ontology impact cannot currently be determined from available governed
          provenance.
        </p>
      </div>
    );
  }

  if (impact.outcome === "NO_IMPACT") {
    return (
      <div>
        <h3>Ontology Impact</h3>
        <p>No ontology impact identified for this Finding.</p>
      </div>
    );
  }

  const exposures = impact.propagated_impacts;
  const primary = primaryExposure(exposures);
  const count = exposures.length;

  return (
    <div>
      <h3>Ontology Impact</h3>
      {count > 0 ? (
        <p>
          This unresolved finding exposes <strong>{count}</strong> downstream{" "}
          {count === 1 ? "entity" : "entities"} through governed ontology
          dependencies.
        </p>
      ) : (
        <p>
          No governed propagated exposure is recorded for this Finding. Only its
          directly impacted entity is shown.
        </p>
      )}

      {primary && primary.paths.length > 0 ? (
        <section aria-label="Primary exposure path">
          <h4>{primary.entity_name} is exposed through this governed path</h4>
          <ImpactChain path={primary.paths[0]} />
          <p className="muted">
            Exposure through a governed dependency path — not a claim that any
            source value is true, and not a measure of criticality.
          </p>
        </section>
      ) : null}

      {count > 0 ? (
        <section aria-label="Exposed entities">
          <h4>Exposed entities</h4>
          <ul>
            {exposures.map((item) => (
              <li key={item.entity_id}>
                <details>
                  <summary>
                    {item.entity_name}{" "}
                    <span className="muted">
                      ({item.entity_type_name}, {item.depth}{" "}
                      {item.depth === 1 ? "hop" : "hops"})
                    </span>
                  </summary>
                  {item.paths.map((path, index) => (
                    <p key={index}>{path.map(hopSentence).join(" · ")}</p>
                  ))}
                  {item.paths.length === MAX_RETAINED_PATHS ? (
                    <p className="muted">
                      Showing the {MAX_RETAINED_PATHS} shortest governed paths.
                    </p>
                  ) : null}
                </details>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <details style={{ marginTop: "0.75rem" }}>
        <summary>Accessible path detail</summary>
        <ul>
          {impact.direct_entity_id ? (
            <li>
              Direct impact: {impact.direct_entity_type ?? "Entity"}
              {primary && primary.paths[0]?.[0]
                ? ` — ${primary.paths[0][0].from_entity_name}`
                : ""}
            </li>
          ) : null}
          {exposures.map((item) =>
            item.paths.map((path, index) => (
              <li key={`${item.entity_id}-${index}`}>
                Exposed {item.entity_name}: {path.map(hopSentence).join(" · ")}
              </li>
            )),
          )}
        </ul>
      </details>
    </div>
  );
}
