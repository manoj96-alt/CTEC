"use client";

import { useMemo, useState, type CSSProperties } from "react";
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  Position,
  type Edge,
  type Node,
  type NodeMouseHandler,
} from "reactflow";
import "reactflow/dist/style.css";
import type { Concept, Relationship } from "@/lib/ontology-studio/contracts";

const LAYER_COLUMN_WIDTH = 260;
const NODE_ROW_HEIGHT = 96;

export interface LayeredLayout {
  positions: Record<string, { x: number; y: number }>;
  layerOf: Record<string, number>;
}

// WOW-I3-B-R1: a deterministic layered layout derived only from the real,
// governed source_concept -> target_concept edges (longest-path layering,
// a standard Sugiyama-style technique) -- no new dependency, no invented
// process stage, chronology, or cardinality. Layer/column position is a
// rendering strategy only; it is never a new ontology fact. Exported so
// its determinism and direction-fidelity can be unit-tested directly,
// independent of ReactFlow/DOM rendering.
export function computeLayeredLayout(
  concepts: Concept[],
  relationships: Relationship[],
): LayeredLayout {
  const names = concepts.map((c) => c.name);
  const nameSet = new Set(names);
  const validRelationships = relationships.filter(
    (r) => nameSet.has(r.source_concept) && nameSet.has(r.target_concept),
  );

  // Longest-path-from-source layering. Cycle-safe: capped at `names.length`
  // relaxation passes, so a cycle simply stops growing rather than looping
  // forever -- still deterministic, still never fabricates meaning.
  const layerOf: Record<string, number> = {};
  names.forEach((n) => {
    layerOf[n] = 0;
  });
  for (let pass = 0; pass < names.length; pass++) {
    let changed = false;
    for (const r of validRelationships) {
      const proposed = layerOf[r.source_concept] + 1;
      if (proposed > layerOf[r.target_concept]) {
        layerOf[r.target_concept] = proposed;
        changed = true;
      }
    }
    if (!changed) break;
  }

  const maxLayer = names.length ? Math.max(...names.map((n) => layerOf[n])) : 0;
  const layers: string[][] = Array.from({ length: maxLayer + 1 }, () => []);
  names.forEach((n) => layers[layerOf[n]].push(n));

  // One left-to-right barycenter pass: order each layer (after the first)
  // by the average column-position of its already-placed real predecessors,
  // to reduce edge crossings. Deterministic and stable (ties fall back to
  // original concept order).
  const orderIndex: Record<string, number> = {};
  layers[0].forEach((n, i) => {
    orderIndex[n] = i;
  });
  for (let layerIdx = 1; layerIdx <= maxLayer; layerIdx++) {
    const layer = layers[layerIdx];
    const barycenter = new Map<string, number>();
    layer.forEach((n) => {
      const preds = validRelationships
        .filter(
          (r) =>
            r.target_concept === n &&
            layerOf[r.source_concept] === layerIdx - 1,
        )
        .map((r) => orderIndex[r.source_concept]);
      barycenter.set(
        n,
        preds.length
          ? preds.reduce((a, b) => a + b, 0) / preds.length
          : Number.MAX_SAFE_INTEGER,
      );
    });
    layer.sort((a, b) => {
      const diff = (barycenter.get(a) ?? 0) - (barycenter.get(b) ?? 0);
      return diff !== 0 ? diff : names.indexOf(a) - names.indexOf(b);
    });
    layer.forEach((n, i) => {
      orderIndex[n] = i;
    });
  }

  const maxLayerSize = Math.max(1, ...layers.map((l) => l.length));
  const positions: Record<string, { x: number; y: number }> = {};
  layers.forEach((layer, layerIdx) => {
    const verticalOffset =
      ((maxLayerSize - layer.length) * NODE_ROW_HEIGHT) / 2;
    layer.forEach((name, i) => {
      positions[name] = {
        x: layerIdx * LAYER_COLUMN_WIDTH,
        y: verticalOffset + i * NODE_ROW_HEIGHT,
      };
    });
  });

  return { positions, layerOf };
}

type NodeTier = "selected" | "connected" | "muted" | "default";

// All tiers render inside the dark `.obs-ontology-canvas` (CDD-083 §5.2),
// so every color here is an --obs-* dark-canvas-appropriate token, never
// the light-panel --muted/--line tokens used outside the canvas.
function nodeStyleFor(tier: NodeTier): CSSProperties {
  switch (tier) {
    case "selected":
      return {
        border: "2px solid var(--obs-intelligence)",
        borderRadius: "0.6rem",
        padding: "0.55rem 0.8rem",
        fontSize: "0.8rem",
        fontWeight: 700,
        background: "var(--obs-surface-interactive)",
        color: "var(--obs-text-primary)",
        boxShadow:
          "0 0 0 3px color-mix(in oklch, var(--obs-intelligence) 22%, transparent)",
      };
    case "connected":
      return {
        border:
          "1px solid color-mix(in oklch, var(--obs-intelligence) 55%, var(--obs-border-strong))",
        borderRadius: "0.6rem",
        padding: "0.5rem 0.75rem",
        fontSize: "0.8rem",
        fontWeight: 600,
        background: "var(--obs-surface-interactive)",
        color: "var(--obs-text-primary)",
      };
    case "muted":
      return {
        border: "1px solid var(--obs-border-strong)",
        borderRadius: "0.6rem",
        padding: "0.5rem 0.75rem",
        fontSize: "0.8rem",
        fontWeight: 500,
        background: "var(--obs-surface)",
        color: "var(--obs-text-muted)",
        opacity: 0.55,
      };
    default:
      return {
        border: "1px solid var(--obs-border-strong)",
        borderRadius: "0.6rem",
        padding: "0.5rem 0.75rem",
        fontSize: "0.8rem",
        fontWeight: 600,
        background: "var(--obs-surface-elevated)",
        color: "var(--obs-text-primary)",
      };
  }
}

export function OntologyGraph({
  concepts,
  relationships,
}: {
  concepts: Concept[];
  relationships: Relationship[];
}) {
  const [selectedName, setSelectedName] = useState<string | null>(null);

  const nameSet = useMemo(
    () => new Set(concepts.map((c) => c.name)),
    [concepts],
  );
  const validRelationships = useMemo(
    () =>
      relationships.filter(
        (r) => nameSet.has(r.source_concept) && nameSet.has(r.target_concept),
      ),
    [relationships, nameSet],
  );

  const connectedNames = useMemo(() => {
    if (selectedName == null) return new Set<string>();
    const set = new Set<string>();
    validRelationships.forEach((r) => {
      if (r.source_concept === selectedName) set.add(r.target_concept);
      if (r.target_concept === selectedName) set.add(r.source_concept);
    });
    return set;
  }, [validRelationships, selectedName]);

  const { nodes, edges } = useMemo(() => {
    const { positions } = computeLayeredLayout(concepts, validRelationships);

    const flowNodes: Node[] = concepts.map((concept) => {
      const tier: NodeTier =
        selectedName == null
          ? "default"
          : concept.name === selectedName
            ? "selected"
            : connectedNames.has(concept.name)
              ? "connected"
              : "muted";
      return {
        id: concept.name,
        position: positions[concept.name] ?? { x: 0, y: 0 },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: { label: concept.name },
        style: nodeStyleFor(tier),
      };
    });

    const flowEdges: Edge[] = validRelationships.map((relationship) => {
      const touchesSelected =
        selectedName != null &&
        (relationship.source_concept === selectedName ||
          relationship.target_concept === selectedName);
      const muted = selectedName != null && !touchesSelected;
      // A structural connector line, not free-standing muted text --
      // --obs-border-strong / --obs-intelligence are the tokens designed
      // for exactly this, inside the dark canvas.
      const stroke = touchesSelected
        ? "var(--obs-intelligence)"
        : "var(--obs-border-strong)";

      return {
        id: `${relationship.source_concept}-${relationship.name}-${relationship.target_concept}`,
        source: relationship.source_concept,
        target: relationship.target_concept,
        label: relationship.name,
        animated: false,
        style: {
          stroke,
          strokeWidth: touchesSelected ? 2 : 1,
          opacity: muted ? 0.3 : 1,
        },
        labelStyle: {
          fill: touchesSelected
            ? "var(--obs-text-primary)"
            : "var(--obs-text-secondary)",
          fontSize: 11,
          fontWeight: touchesSelected ? 700 : 500,
        },
        labelBgStyle: {
          fill: "var(--obs-canvas-deep)",
          fillOpacity: muted ? 0.4 : 0.85,
        },
        labelBgPadding: [4, 2] as [number, number],
        labelBgBorderRadius: 3,
        // Direction is the real source_concept -> target_concept edge only
        // -- the arrow renders that fact, it never implies a business
        // process sequence beyond it.
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: stroke,
          width: 14,
          height: 14,
        },
      };
    });

    return { nodes: flowNodes, edges: flowEdges };
  }, [concepts, validRelationships, selectedName, connectedNames]);

  const handleNodeClick: NodeMouseHandler = (_event, node) => {
    setSelectedName(node.id);
  };

  const selectedConcept = concepts.find((c) => c.name === selectedName) ?? null;
  const outgoing = validRelationships.filter(
    (r) => r.source_concept === selectedName,
  );
  const incoming = validRelationships.filter(
    (r) => r.target_concept === selectedName,
  );

  return (
    <section className="panel" style={{ marginTop: "1.5rem" }}>
      <p className="eyebrow">Ontology Graph</p>
      <h2 style={{ marginTop: "0.25rem" }}>
        Governed Concepts &amp; Relationships
      </h2>
      {/* CDD-083 §13: a compact, truthful orientation cue -- direction
          shown in the graph is exactly the real relationship direction,
          never an implied business process or chronology. */}
      <p className="obs-ontology-caption">
        Relationship direction follows the governed ontology.
      </p>
      {/* CDD-083 §5.2: the canvas itself (not the surrounding .panel --
          the established light/dark two-surface contract is unchanged)
          gets a dark, Observatory-native background, giving the
          flagship graph real depth without a page-level dark-mode
          flip. Node/edge/legend tokens below are chosen to read
          correctly against this specific background. */}
      <div
        className="obs-ontology-canvas"
        role="img"
        aria-label="Ontology concept and relationship graph"
      >
        {nodes.length > 0 ? (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodeClick={handleNodeClick}
            nodesDraggable={false}
            fitView
          >
            <Background />
            <Controls />
          </ReactFlow>
        ) : (
          <div style={{ padding: "1.5rem", color: "var(--obs-text-muted)" }}>
            No concepts are available from the ontology service yet.
          </div>
        )}
      </div>

      {/* CDD-062 §13: static legend explaining only the visual semantics
          the graph above already has -- no new interaction, no new data,
          no new graph library. "Connected concept" is added only because
          the connected-tier state above is actually rendered. */}
      <div className="graph-legend" aria-label="Graph legend">
        <span className="graph-legend-item">
          <span
            className="graph-legend-swatch graph-legend-swatch--selected"
            aria-hidden="true"
          />
          Selected concept
        </span>
        <span className="graph-legend-item">
          <span
            className="graph-legend-swatch graph-legend-swatch--connected"
            aria-hidden="true"
          />
          Connected concept
        </span>
        <span className="graph-legend-item">
          <span
            className="graph-legend-swatch graph-legend-swatch--unselected"
            aria-hidden="true"
          />
          Unselected concept
        </span>
        <span className="graph-legend-item">
          <span
            className="graph-legend-swatch graph-legend-swatch--edge"
            aria-hidden="true"
          />
          Governed relationship
        </span>
      </div>

      {/* Readable fallback list — always rendered, not conditional on the
          graph, so the demo never depends solely on canvas rendering.
          Collapsed by default (progressive disclosure) behind a native,
          keyboard-operable <details>/<summary> -- content stays present
          in the DOM and queryable, so the accessibility contract is not
          weakened. */}
      <details className="obs-ontology-relationship-details">
        <summary>Relationship details ({relationships.length})</summary>
        <ul>
          {relationships.map((r) => (
            <li key={`${r.source_concept}-${r.name}-${r.target_concept}`}>
              {r.source_concept} — {r.name} → {r.target_concept}
            </li>
          ))}
        </ul>
      </details>

      {selectedConcept && (
        <div
          className="panel obs-ontology-inspector"
          style={{ marginTop: "1rem" }}
        >
          <p className="eyebrow">Concept</p>
          <p
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              fontWeight: 700,
              fontSize: "1.05rem",
              marginTop: "0.25rem",
            }}
          >
            <span>{selectedConcept.name}</span>
            {/* CDD-083 §5.3: discovery_label is a real, already-fetched
                field that was previously never rendered anywhere --
                answers "what does Noetva actually know vs. merely
                visualize" truthfully, without inventing a new field. */}
            <span className="status-tag">
              {selectedConcept.discovery_label === "curated"
                ? "Curated"
                : "Auto-discovered"}
            </span>
          </p>
          <dl className="obs-ontology-inspector-meta">
            <div>
              <dt>Governance</dt>
              <dd>
                <span className="status-tag">
                  {selectedConcept.governance_status}
                </span>
              </dd>
            </div>
            <div>
              <dt>Lifecycle</dt>
              <dd>
                <span className="status-tag">
                  {selectedConcept.lifecycle_state}
                </span>
              </dd>
            </div>
            <div>
              <dt>Version</dt>
              <dd>{selectedConcept.version_number}</dd>
            </div>
            <div>
              <dt>Technical ID</dt>
              <dd className="mono">{selectedConcept.entity_type_id}</dd>
            </div>
          </dl>
          <p style={{ color: "var(--muted)", marginTop: "0.5rem" }}>
            {selectedConcept.definition || "No definition available."}
          </p>
          <p style={{ fontSize: "0.75rem", color: "var(--muted)" }}>
            Definition source: {selectedConcept.definition_source}
          </p>

          <div className="obs-ontology-relationships">
            <div>
              <p style={{ fontWeight: 600, fontSize: "0.85rem" }}>Incoming</p>
              {incoming.length ? (
                <ul>
                  {incoming.map((r) => (
                    <li key={`in-${r.source_concept}-${r.name}`}>
                      {r.source_concept} — {r.name} → {selectedConcept.name}
                    </li>
                  ))}
                </ul>
              ) : (
                <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
                  none
                </p>
              )}
            </div>
            <div>
              <p style={{ fontWeight: 600, fontSize: "0.85rem" }}>Outgoing</p>
              {outgoing.length ? (
                <ul>
                  {outgoing.map((r) => (
                    <li key={`out-${r.name}-${r.target_concept}`}>
                      {selectedConcept.name} — {r.name} → {r.target_concept}
                    </li>
                  ))}
                </ul>
              ) : (
                <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
                  none
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
