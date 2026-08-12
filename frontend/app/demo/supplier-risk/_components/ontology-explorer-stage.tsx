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
import type { OntologyModel, OntologyNode } from "@/lib/demo/ontology-model";

export interface OntologyExplorerStageProps {
  model: OntologyModel;
  onContinue: () => void;
}

const NODE_POSITIONS: Record<string, { x: number; y: number }> = {
  "supplier:SUP-001": { x: 20, y: 60 },
  "material:MAT-100": { x: 260, y: 60 },
  "product:PROD-01": { x: 500, y: 60 },
  "facility:FAC-01": { x: 740, y: 60 },
  "revenue:primary": { x: 980, y: 60 },
  "region:REG-EA": { x: 20, y: 240 },
  "riskEvent:RE-001": { x: 20, y: 400 },
  "agreement:SA-100": { x: 260, y: 240 },
  "candidate:SUP-002": { x: 260, y: 400 },
};

const KIND_COLOR: Record<OntologyNode["kind"], string> = {
  supplier: "var(--accent)",
  candidateSupplier: "var(--success)",
  material: "var(--accent)",
  product: "var(--accent)",
  facility: "var(--accent)",
  revenue: "var(--accent-strong)",
  region: "var(--muted)",
  riskEvent: "var(--danger)",
  agreement: "var(--muted)",
};

function toFlowNode(
  node: OntologyNode,
  isDimmed: boolean,
  isSelected: boolean,
): Node {
  const isCandidate = node.kind === "candidateSupplier";
  return {
    id: node.id,
    position: NODE_POSITIONS[node.id] ?? { x: 0, y: 0 },
    data: { label: node.label },
    style: {
      border: `2px ${isCandidate ? "dashed" : "solid"} ${KIND_COLOR[node.kind]}`,
      borderRadius: "0.6rem",
      background: "white",
      padding: "0.5rem 0.75rem",
      fontSize: "0.8rem",
      fontWeight: isSelected ? 700 : 500,
      opacity: isDimmed ? 0.25 : 1,
      boxShadow: isSelected ? "0 0 0 3px rgba(14,79,99,0.25)" : "none",
      width: 200,
    },
  };
}

function toFlowEdge(
  edge: OntologyModel["edges"][number],
  dimmed: boolean,
): Edge {
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.label,
    animated: false,
    style: {
      stroke: dimmed ? "var(--line)" : "var(--accent)",
      opacity: dimmed ? 0.3 : 1,
    },
    labelStyle: { fontSize: 11, fill: "var(--muted)" },
  };
}

export function OntologyExplorerStage({
  model,
  onContinue,
}: OntologyExplorerStageProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [highlightRiskPath, setHighlightRiskPath] = useState(false);

  const selectedNode = useMemo(
    () => model.nodes.find((node) => node.id === selectedNodeId) ?? null,
    [model.nodes, selectedNodeId],
  );

  const flowNodes = useMemo(
    () =>
      model.nodes.map((node) =>
        toFlowNode(
          node,
          highlightRiskPath && !node.onRiskPath,
          node.id === selectedNodeId,
        ),
      ),
    [model.nodes, highlightRiskPath, selectedNodeId],
  );

  const flowEdges = useMemo(
    () =>
      model.edges.map((edge) =>
        toFlowEdge(edge, highlightRiskPath && !edge.onRiskPath),
      ),
    [model.edges, highlightRiskPath],
  );

  const handleNodeClick: NodeMouseHandler = (_event, node) => {
    setSelectedNodeId(node.id);
  };

  const { impactSummary } = model;

  return (
    <section>
      <p className="eyebrow">Stage 3 of 5</p>
      <h2 style={{ marginTop: "0.25rem" }}>Explore Ontology</h2>
      <p style={{ color: "var(--muted)", maxWidth: "42rem" }}>
        These relationships were built from the mappings you just accepted.
        Select any node to see the source record behind it.
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(9rem, 1fr))",
          gap: "0.75rem",
          margin: "1.25rem 0",
        }}
      >
        <div className="panel" style={{ padding: "0.75rem" }}>
          <p style={{ margin: 0, fontSize: "1.4rem", fontWeight: 800 }}>
            {impactSummary.criticalSuppliersAffected}
          </p>
          <p style={{ margin: 0, fontSize: "0.78rem", color: "var(--muted)" }}>
            Critical supplier affected
          </p>
        </div>
        <div className="panel" style={{ padding: "0.75rem" }}>
          <p style={{ margin: 0, fontSize: "1.4rem", fontWeight: 800 }}>
            {impactSummary.criticalMaterialsAffected}
          </p>
          <p style={{ margin: 0, fontSize: "0.78rem", color: "var(--muted)" }}>
            Critical material affected
          </p>
        </div>
        <div className="panel" style={{ padding: "0.75rem" }}>
          <p style={{ margin: 0, fontSize: "1.4rem", fontWeight: 800 }}>
            {impactSummary.productsAffected}
          </p>
          <p style={{ margin: 0, fontSize: "0.78rem", color: "var(--muted)" }}>
            Product affected
          </p>
        </div>
        <div className="panel" style={{ padding: "0.75rem" }}>
          <p style={{ margin: 0, fontSize: "1.4rem", fontWeight: 800 }}>
            {impactSummary.facilitiesExposed}
          </p>
          <p style={{ margin: 0, fontSize: "0.78rem", color: "var(--muted)" }}>
            Assembly facility exposed
          </p>
        </div>
        <div className="panel" style={{ padding: "0.75rem" }}>
          <p style={{ margin: 0, fontSize: "1.4rem", fontWeight: 800 }}>
            ${(impactSummary.annualRevenueExposureUsd / 1_000_000).toFixed(0)}M
          </p>
          <p style={{ margin: 0, fontSize: "0.78rem", color: "var(--muted)" }}>
            Annual revenue exposure
          </p>
        </div>
        <div className="panel" style={{ padding: "0.75rem" }}>
          <p style={{ margin: 0, fontSize: "1.4rem", fontWeight: 800 }}>
            {impactSummary.secondarySourceActive ? "Yes" : "No"}
          </p>
          <p style={{ margin: 0, fontSize: "0.78rem", color: "var(--muted)" }}>
            Active secondary source
          </p>
        </div>
      </div>

      <label
        style={{
          display: "inline-flex",
          gap: "0.5rem",
          alignItems: "center",
          fontSize: "0.85rem",
          color: "var(--muted)",
          marginBottom: "0.75rem",
        }}
      >
        <input
          type="checkbox"
          checked={highlightRiskPath}
          onChange={(event) => setHighlightRiskPath(event.target.checked)}
        />
        Highlight risk path
      </label>

      <div
        style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1rem" }}
      >
        <div
          className="panel"
          style={{ height: "26rem", padding: 0 }}
          data-testid="ontology-graph"
        >
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            onNodeClick={handleNodeClick}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Background />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>

        <div className="panel" style={{ padding: "1rem" }}>
          <p style={{ fontWeight: 700, marginBottom: "0.5rem" }}>
            Source evidence
          </p>
          {!selectedNode && (
            <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
              Select a node in the graph to see the record it came from.
            </p>
          )}
          {selectedNode && (
            <div data-testid="node-inspector">
              <p style={{ fontWeight: 700 }}>{selectedNode.label}</p>
              <ul
                style={{
                  paddingLeft: "1.1rem",
                  fontSize: "0.85rem",
                  color: "var(--muted)",
                }}
              >
                {selectedNode.detailLines.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
              <p
                style={{
                  fontSize: "0.78rem",
                  color: "var(--muted)",
                  marginTop: "0.75rem",
                }}
              >
                Source:{" "}
                {selectedNode.sourceRefs
                  .map((ref) => `${ref.file} (row ${ref.rowIndex + 1})`)
                  .join(", ")}
              </p>
            </div>
          )}
        </div>
      </div>

      <button
        type="button"
        onClick={onContinue}
        style={{ marginTop: "1.5rem" }}
      >
        Continue to Decision Flow
      </button>
    </section>
  );
}
