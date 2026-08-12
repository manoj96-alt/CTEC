"use client";

import { resolveScenarioFacts } from "@/lib/demo/scenario-facts";
import { buildOntologyModel } from "@/lib/demo/ontology-model";
import type { DemoDataset } from "@/lib/demo/types";

export interface DatasetRelationshipSummaryProps {
  dataset: DemoDataset;
}

export function DatasetRelationshipSummary({
  dataset,
}: DatasetRelationshipSummaryProps) {
  const resolution = resolveScenarioFacts(dataset);
  const model = resolution.complete ? buildOntologyModel(resolution) : null;

  return (
    <section className="panel">
      <p className="eyebrow">Detected Relationship Keys</p>
      <p style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
        Fields with matching names across two or more files, detected from the
        imported column headers.
      </p>
      <ul
        style={{
          margin: "0.5rem 0 0",
          paddingLeft: "1.2rem",
          fontSize: "0.85rem",
        }}
      >
        {dataset.relationshipKeys.map((key) => (
          <li key={key.fieldName}>
            {key.fieldName} — links {key.files.join(" ↔ ")}
          </li>
        ))}
      </ul>

      <p className="eyebrow" style={{ marginTop: "1.5rem" }}>
        Sample Scenario Relationships
      </p>
      <p style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
        This is one sample scenario used by the Supplier Risk demo, not a
        comprehensive relationship map of every record in these files.
      </p>
      {model ? (
        <ul
          style={{
            margin: "0.5rem 0 0",
            paddingLeft: "1.2rem",
            fontSize: "0.85rem",
          }}
        >
          {model.edges.map((edge) => {
            const source = model.nodes.find((n) => n.id === edge.source);
            const target = model.nodes.find((n) => n.id === edge.target);
            return (
              <li key={edge.id}>
                {source?.label ?? edge.source} —{edge.label}→{" "}
                {target?.label ?? edge.target}
              </li>
            );
          })}
        </ul>
      ) : (
        <p role="status" style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
          The sample scenario relationships could not be resolved from the
          current data.
        </p>
      )}
    </section>
  );
}
