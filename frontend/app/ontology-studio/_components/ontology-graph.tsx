"use client";

import { useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  type Edge,
  type Node,
  type NodeMouseHandler,
} from "reactflow";
import "reactflow/dist/style.css";
import type { Concept, Relationship } from "@/lib/ontology-studio/contracts";

const COLUMN_WIDTH = 220;
const ROW_HEIGHT = 110;

export function OntologyGraph({
  concepts,
  relationships,
}: {
  concepts: Concept[];
  relationships: Relationship[];
}) {
  const [selectedName, setSelectedName] = useState<string | null>(null);

  const { nodes, edges } = useMemo(() => {
    const positions: Record<string, { x: number; y: number }> = {};
    concepts.forEach((concept, index) => {
      positions[concept.name] = {
        x: (index % 4) * COLUMN_WIDTH,
        y: Math.floor(index / 4) * ROW_HEIGHT,
      };
    });

    const flowNodes: Node[] = concepts.map((concept) => ({
      id: concept.name,
      position: positions[concept.name] ?? { x: 0, y: 0 },
      data: { label: concept.name },
      style: {
        border:
          concept.name === selectedName
            ? "2px solid var(--accent-strong)"
            : "1px solid var(--line)",
        borderRadius: "0.5rem",
        padding: "0.5rem",
        fontSize: "0.8rem",
        background: "white",
      },
    }));

    const flowEdges: Edge[] = relationships.map((relationship) => ({
      id: `${relationship.source_concept}-${relationship.name}-${relationship.target_concept}`,
      source: relationship.source_concept,
      target: relationship.target_concept,
      label: relationship.name,
      animated: false,
      style: { stroke: "var(--muted)" },
    }));

    return { nodes: flowNodes, edges: flowEdges };
  }, [concepts, relationships, selectedName]);

  const handleNodeClick: NodeMouseHandler = (_event, node) => {
    setSelectedName(node.id);
  };

  const selectedConcept = concepts.find((c) => c.name === selectedName) ?? null;
  const outgoing = relationships.filter(
    (r) => r.source_concept === selectedName,
  );
  const incoming = relationships.filter(
    (r) => r.target_concept === selectedName,
  );

  return (
    <section className="panel" style={{ marginTop: "1.5rem" }}>
      <p className="eyebrow">Ontology Graph</p>
      <h2 style={{ marginTop: "0.25rem" }}>
        Governed Concepts &amp; Relationships
      </h2>
      <div
        style={{
          marginTop: "1rem",
          height: "22rem",
          border: "1px solid var(--line)",
          borderRadius: "0.5rem",
        }}
        role="img"
        aria-label="Ontology concept and relationship graph"
      >
        {nodes.length > 0 ? (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodeClick={handleNodeClick}
            fitView
          >
            <Background />
            <Controls />
          </ReactFlow>
        ) : (
          <div style={{ padding: "1.5rem", color: "var(--muted)" }}>
            No concepts are available from the ontology service yet.
          </div>
        )}
      </div>

      {/* Readable fallback list — always rendered, not conditional on the
          graph, so the demo never depends solely on canvas rendering. */}
      <ul
        style={{
          marginTop: "1rem",
          paddingLeft: "1.2rem",
          fontSize: "0.85rem",
          color: "var(--muted)",
        }}
      >
        {relationships.map((r) => (
          <li key={`${r.source_concept}-${r.name}-${r.target_concept}`}>
            {r.source_concept} — {r.name} → {r.target_concept}
          </li>
        ))}
      </ul>

      {selectedConcept && (
        <div className="panel" style={{ marginTop: "1rem" }}>
          <p style={{ fontWeight: 700 }}>{selectedConcept.name}</p>
          <p style={{ color: "var(--muted)", marginTop: "0.25rem" }}>
            {selectedConcept.definition || "No definition available."}
          </p>
          <dl style={{ marginTop: "0.5rem", fontSize: "0.85rem" }}>
            <div>
              <strong>Technical ID:</strong> {selectedConcept.entity_type_id}
            </div>
            <div>
              <strong>Lifecycle state:</strong>{" "}
              {selectedConcept.lifecycle_state}
            </div>
            <div>
              <strong>Governance status:</strong>{" "}
              {selectedConcept.governance_status}
            </div>
            <div>
              <strong>Version:</strong> {selectedConcept.version_number}
            </div>
            <div>
              <strong>Definition source:</strong>{" "}
              {selectedConcept.definition_source}
            </div>
          </dl>
          <p style={{ marginTop: "0.5rem", fontSize: "0.85rem" }}>
            <strong>Outgoing relationships:</strong>{" "}
            {outgoing.length
              ? outgoing
                  .map((r) => `${r.name} → ${r.target_concept}`)
                  .join(", ")
              : "none"}
          </p>
          <p style={{ fontSize: "0.85rem" }}>
            <strong>Incoming relationships:</strong>{" "}
            {incoming.length
              ? incoming
                  .map((r) => `${r.source_concept} — ${r.name}`)
                  .join(", ")
              : "none"}
          </p>
        </div>
      )}
    </section>
  );
}
