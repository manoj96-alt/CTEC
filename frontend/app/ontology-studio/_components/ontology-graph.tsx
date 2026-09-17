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
// independent of ReactFlow/DOM rendering. WOW-I3-B-R2: retained exactly
// as the "ontology overview" (nothing selected) layout -- see
// `computeEgoLayout` below for the selected-concept mode, which replaces
// this for the local-focus experience.
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

export interface EgoLayout {
  positions: Record<string, { x: number; y: number }>;
  leftNames: string[];
  rightNames: string[];
  contextNames: string[];
}

const EGO_LANE_GAP = 280;
const EGO_ROW_HEIGHT = 84;
const EGO_CONTEXT_ROW_GAP = 110;
const EGO_CONTEXT_COLUMNS = 4;
const EGO_CONTEXT_COLUMN_WIDTH = 220;

// WOW-I3-B-R2: the operator's own review found the global layered layout
// technically truthful but cognitively weak -- a relationship that has to
// "skip" a layer (e.g. Supplier, layer 0, -> Contract, layer 2, because
// Contract's own layer is driven by its OTHER real predecessor Material)
// is forced to visually cross through the intermediate layer's nodes and
// edges, making a single real relationship hard to trace by eye. Global
// edge/label styling alone cannot fix this -- it is a layout problem.
//
// This is a dedicated three-lane ego (local-focus) layout, used only
// while a concept is selected: every concept with a real incoming edge
// to the selection is placed in a left column; every concept with a real
// outgoing edge from the selection in a right column; the selection
// itself is centered between them. Every direct relationship therefore
// gets its own short, dedicated lane between two fixed columns -- it can
// never have to cross through an unrelated layer. Every remaining
// concept (no direct edge to the selection) is kept fully present, never
// removed, in a compact muted cluster positioned below the focus lanes
// so it cannot visually compete with them.
//
// A concept that is simultaneously a real incoming source AND a real
// outgoing target of the selection (not present in the current supplier-
// risk ontology, but not excluded by the contract) is positioned once,
// on the right/outgoing lane -- this is a purely cosmetic tie-break; the
// textual Incoming/Outgoing lists in the inspector are derived
// independently from the real relationships and list it correctly under
// both headings regardless of where it is drawn.
//
// Purely a rendering strategy: no new ontology fact, no fabricated
// hierarchy, chronology, or process sequence. Exported so its
// determinism and direction-fidelity can be unit-tested directly.
export function computeEgoLayout(
  concepts: Concept[],
  relationships: Relationship[],
  selectedName: string,
): EgoLayout {
  const names = concepts.map((c) => c.name);
  const nameSet = new Set(names);
  const validRelationships = relationships.filter(
    (r) => nameSet.has(r.source_concept) && nameSet.has(r.target_concept),
  );

  const incomingNames = Array.from(
    new Set(
      validRelationships
        .filter(
          (r) =>
            r.target_concept === selectedName &&
            r.source_concept !== selectedName,
        )
        .map((r) => r.source_concept),
    ),
  );
  const outgoingNames = Array.from(
    new Set(
      validRelationships
        .filter(
          (r) =>
            r.source_concept === selectedName &&
            r.target_concept !== selectedName,
        )
        .map((r) => r.target_concept),
    ),
  );
  const outgoingSet = new Set(outgoingNames);
  const leftNames = incomingNames.filter((n) => !outgoingSet.has(n));
  const rightNames = outgoingNames;
  const focusNames = new Set([selectedName, ...leftNames, ...rightNames]);
  const contextNames = names.filter((n) => !focusNames.has(n));

  const positions: Record<string, { x: number; y: number }> = {};
  positions[selectedName] = { x: 0, y: 0 };

  const laneY = (count: number, index: number) =>
    (index - (count - 1) / 2) * EGO_ROW_HEIGHT;

  leftNames.forEach((n, i) => {
    positions[n] = { x: -EGO_LANE_GAP, y: laneY(leftNames.length, i) };
  });
  rightNames.forEach((n, i) => {
    positions[n] = { x: EGO_LANE_GAP, y: laneY(rightNames.length, i) };
  });

  const focusRows = Math.max(leftNames.length, rightNames.length, 1);
  const contextTop = (focusRows / 2) * EGO_ROW_HEIGHT + EGO_CONTEXT_ROW_GAP;
  contextNames.forEach((n, i) => {
    const col = i % EGO_CONTEXT_COLUMNS;
    const row = Math.floor(i / EGO_CONTEXT_COLUMNS);
    positions[n] = {
      x: (col - (EGO_CONTEXT_COLUMNS - 1) / 2) * EGO_CONTEXT_COLUMN_WIDTH,
      y: contextTop + row * EGO_ROW_HEIGHT,
    };
  });

  return { positions, leftNames, rightNames, contextNames };
}

export interface FocusSubgraph {
  concepts: Concept[];
  relationships: Relationship[];
}

// WOW-I3-B-R3: operator visual evidence on R2 showed that even though the
// selected concept and its direct neighbors were now unmistakable, the
// muted context concepts' OWN relationships (e.g. usedIn, candidateFor,
// exposedTo when Supplier is selected) still rendered inside the same
// canvas -- visually competing with the focused relationships even at low
// opacity. This derives a strict, real-data-only subgraph: the selected
// concept, every concept with a real direct relationship to it, and only
// those real incident relationships. This is PRESENTATIONAL filtering of
// what the focused ReactFlow canvas renders -- the complete ontology is
// never mutated, remains fully queryable via Overview mode and the
// Relationship Details inventory below, and this function contains no
// concept-name-specific logic (works for any selected concept, in any
// ontology). Exported so its derivation can be unit-tested directly.
export function computeFocusSubgraph(
  concepts: Concept[],
  relationships: Relationship[],
  selectedName: string,
): FocusSubgraph {
  const nameSet = new Set(concepts.map((c) => c.name));
  const incident = relationships.filter(
    (r) =>
      nameSet.has(r.source_concept) &&
      nameSet.has(r.target_concept) &&
      (r.source_concept === selectedName || r.target_concept === selectedName),
  );
  const focusNames = new Set<string>([selectedName]);
  incident.forEach((r) => {
    focusNames.add(r.source_concept);
    focusNames.add(r.target_concept);
  });
  return {
    concepts: concepts.filter((c) => focusNames.has(c.name)),
    relationships: incident,
  };
}

type NodeTier = "selected" | "connected" | "default";

// All tiers render inside the dark `.obs-ontology-canvas` (CDD-083 §5.2),
// so every color here is an --obs-* dark-canvas-appropriate token, never
// the light-panel --muted/--line tokens used outside the canvas. Every
// tier also differs in border WIDTH and font-weight, not color alone.
// WOW-I3-B-R3: the "muted" tier is retired -- the focused canvas now only
// ever renders the selected concept and its direct neighbors (see
// `computeFocusSubgraph`), so there is no longer a third, visually
// competing "unrelated but present" tier inside the canvas.
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

  // WOW-I3-B-R3: the focused ReactFlow canvas renders ONLY the selected
  // concept, concepts with a real direct relationship to it, and those
  // real incident relationships -- derived generically from the actual
  // graph data (no hardcoded concept/relationship names). Overview mode
  // (nothing selected) is completely unaffected: it still renders every
  // real concept and relationship via the unchanged global layered layout.
  const { nodes, edges } = useMemo(() => {
    if (selectedName == null) {
      const { positions } = computeLayeredLayout(concepts, validRelationships);
      const flowNodes: Node[] = concepts.map((concept) => ({
        id: concept.name,
        position: positions[concept.name] ?? { x: 0, y: 0 },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: { label: concept.name },
        style: nodeStyleFor("default"),
      }));
      const flowEdges: Edge[] = validRelationships.map((relationship) => ({
        id: `${relationship.source_concept}-${relationship.name}-${relationship.target_concept}`,
        source: relationship.source_concept,
        target: relationship.target_concept,
        label: relationship.name,
        animated: false,
        type: "smoothstep",
        style: { stroke: "var(--obs-border-strong)", strokeWidth: 1 },
        labelStyle: {
          fill: "var(--obs-text-secondary)",
          fontSize: 11,
          fontWeight: 500,
        },
        labelBgStyle: { fill: "var(--obs-canvas-deep)", fillOpacity: 0.85 },
        labelBgPadding: [4, 2] as [number, number],
        labelBgBorderRadius: 3,
        // Direction is the real source_concept -> target_concept edge only
        // -- the arrow renders that fact, it never implies a business
        // process sequence beyond it.
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: "var(--obs-border-strong)",
          width: 14,
          height: 14,
        },
      }));
      return { nodes: flowNodes, edges: flowEdges };
    }

    const focus = computeFocusSubgraph(
      concepts,
      validRelationships,
      selectedName,
    );
    const { positions } = computeEgoLayout(
      concepts,
      validRelationships,
      selectedName,
    );

    const flowNodes: Node[] = focus.concepts.map((concept) => ({
      id: concept.name,
      position: positions[concept.name] ?? { x: 0, y: 0 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      data: { label: concept.name },
      style: nodeStyleFor(
        concept.name === selectedName ? "selected" : "connected",
      ),
    }));

    // Every relationship in `focus.relationships` is, by construction,
    // directly incident to the selected concept -- there is no longer a
    // "muted, non-incident" edge case inside the focused canvas.
    const flowEdges: Edge[] = focus.relationships.map((relationship) => ({
      id: `${relationship.source_concept}-${relationship.name}-${relationship.target_concept}`,
      source: relationship.source_concept,
      target: relationship.target_concept,
      label: relationship.name,
      animated: false,
      type: "smoothstep",
      style: { stroke: "var(--obs-intelligence)", strokeWidth: 2 },
      labelStyle: {
        fill: "var(--obs-text-primary)",
        fontSize: 11,
        fontWeight: 700,
      },
      labelBgStyle: { fill: "var(--obs-canvas-deep)", fillOpacity: 0.85 },
      labelBgPadding: [4, 2] as [number, number],
      labelBgBorderRadius: 3,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: "var(--obs-intelligence)",
        width: 14,
        height: 14,
      },
    }));

    return { nodes: flowNodes, edges: flowEdges };
  }, [concepts, validRelationships, selectedName]);

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
          never an implied business process or chronology. WOW-I3-B-R3:
          the focus-mode copy no longer claims the rest of the ontology is
          "visible, muted, below" -- it no longer is, inside this canvas --
          and instead truthfully points at how to see it (Overview mode). */}
      <p className="obs-ontology-caption">
        {selectedName == null
          ? "Relationship direction follows the governed ontology. Select a concept to focus on its direct relationships."
          : "Showing direct relationships for the selected concept. Return to overview to see the complete ontology."}
      </p>
      {selectedName != null && (
        <button
          type="button"
          className="secondary"
          onClick={() => setSelectedName(null)}
          style={{ marginTop: "0.5rem" }}
        >
          View full ontology
        </button>
      )}
      {/* CDD-083 §5.2: the canvas itself (not the surrounding .panel --
          the established light/dark two-surface contract is unchanged)
          gets a dark, Observatory-native background, giving the
          flagship graph real depth without a page-level dark-mode
          flip. Node/edge/legend tokens below are chosen to read
          correctly against this specific background. WOW-I3-B-R3: the
          `nodes`/`edges` passed in already ARE the correct set to fit --
          overview gets every real concept, focus mode gets only the
          selected concept + its direct neighbors (computeFocusSubgraph)
          -- so fitView no longer needs a `nodes` filter option. */}
      <div
        className="obs-ontology-canvas"
        role="img"
        aria-label="Ontology concept and relationship graph"
      >
        {nodes.length > 0 ? (
          <ReactFlow
            // Remounting on selection change keeps the fit-to-focus
            // viewport recompute simple and deterministic -- this is a
            // 10-node demo-scale ontology, so a remount is cheap and has
            // no visible cost.
            key={selectedName ?? "__overview__"}
            nodes={nodes}
            edges={edges}
            onNodeClick={handleNodeClick}
            nodesDraggable={false}
            fitView
            fitViewOptions={{ padding: selectedName == null ? 0.2 : 0.4 }}
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
          weakened. Secondary to the graph + selected-concept inspector
          below (CDD-083-R2 §9): a complete inventory for accessibility/
          audit, not a substitute for graph comprehension. */}
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
          <p style={{ color: "var(--muted)", marginTop: "0.5rem" }}>
            {selectedConcept.definition || "No definition available."}
          </p>
          <p style={{ fontSize: "0.75rem", color: "var(--muted)" }}>
            Definition source: {selectedConcept.definition_source}
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

          <div className="obs-ontology-relationships">
            <p className="eyebrow">Connected relationships</p>
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
                  None
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
                  None
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
