"use client";

import ReactFlow, {
  Background,
  Controls,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import type { OntologyImpactResponse } from "@/lib/oqi/contracts";

// CDD-045 §12/§15/§29 -- the graph answers "what ontology knowledge is
// affected?", nothing more. Entity-level nodes only: OQI4 never proved
// attribute-level lineage, so no attribute edge is ever drawn here
// (CDD-045 §38 attribute-lineage honesty). IMPACT_UNKNOWN never renders a
// confident graph path -- it gets its own explicit unknown state instead
// of an empty canvas that could read as "no impact."
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

  const nodes: Node[] = [];
  const edges: Edge[] = [];

  if (impact.direct_entity_id) {
    nodes.push({
      id: "finding",
      position: { x: 0, y: 60 },
      data: { label: "Finding" },
      style: {
        border: "1px solid var(--line)",
        borderRadius: "0.5rem",
        padding: "0.5rem",
      },
    });
    nodes.push({
      id: impact.direct_entity_id,
      position: { x: 220, y: 60 },
      data: { label: `${impact.direct_entity_type ?? "Entity"} (direct)` },
      style: {
        border: "2px solid var(--accent-strong)",
        borderRadius: "0.5rem",
        padding: "0.5rem",
      },
    });
    edges.push({
      id: "finding-direct",
      source: "finding",
      target: impact.direct_entity_id,
      label: "direct impact",
    });
  }

  const propagatedNodes = (impact.propagated_path ?? [])
    .slice()
    .sort((a, b) => a.path_ordinal - b.path_ordinal);

  propagatedNodes.forEach((segment, index) => {
    const nodeId = `path-${segment.relationship_instance_id}-${segment.path_ordinal}`;
    nodes.push({
      id: nodeId,
      position: { x: 440 + index * 200, y: 60 },
      data: { label: `Propagated (${segment.direction})` },
      style: {
        border: "1px dashed var(--line)",
        borderRadius: "0.5rem",
        padding: "0.5rem",
      },
    });
    const previousId =
      index === 0
        ? (impact.direct_entity_id ?? "finding")
        : `path-${propagatedNodes[index - 1].relationship_instance_id}-${propagatedNodes[index - 1].path_ordinal}`;
    edges.push({
      id: `${previousId}-${nodeId}`,
      source: previousId,
      target: nodeId,
      label: "propagated",
      style: { strokeDasharray: "4 4" },
    });
  });

  return (
    <div>
      <h3>Ontology Impact</h3>
      <div
        style={{
          height: "16rem",
          border: "1px solid var(--line)",
          borderRadius: "0.5rem",
        }}
      >
        <ReactFlow nodes={nodes} edges={edges} fitView>
          <Background />
          <Controls />
        </ReactFlow>
      </div>

      <details style={{ marginTop: "0.75rem" }}>
        <summary>Accessible path detail</summary>
        <ul>
          {impact.direct_entity_id ? (
            <li>
              Direct impact: {impact.direct_entity_type ?? "Entity"} (
              {impact.direct_entity_id})
            </li>
          ) : null}
          {propagatedNodes.map((segment) => (
            <li
              key={`${segment.relationship_instance_id}-${segment.path_ordinal}`}
            >
              Propagated step {segment.path_ordinal}: relationship{" "}
              {segment.relationship_instance_id} ({segment.direction})
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
