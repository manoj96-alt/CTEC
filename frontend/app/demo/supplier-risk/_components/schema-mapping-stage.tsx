"use client";

import { useState } from "react";
import { mappingDefinitions } from "@/lib/demo/mapping-definitions";

export interface SchemaMappingStageProps {
  onBuildOntology: () => void;
}

export function SchemaMappingStage({
  onBuildOntology,
}: SchemaMappingStageProps) {
  const [accepted, setAccepted] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(
      mappingDefinitions.map((mapping) => [
        `${mapping.sourceDataset}:${mapping.sourceField}`,
        true,
      ]),
    ),
  );
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  return (
    <section>
      <p className="eyebrow">Stage 2 of 5</p>
      <h2 style={{ marginTop: "0.25rem" }}>Map Schema</h2>
      <p style={{ color: "var(--muted)", maxWidth: "42rem" }}>
        The system detects technical fields in the imported files and proposes
        what each one means in business terms. For this sample dataset the
        proposed mappings are already correct — review them below.
      </p>

      <label
        style={{
          display: "inline-flex",
          gap: "0.5rem",
          alignItems: "center",
          fontSize: "0.85rem",
          color: "var(--muted)",
          margin: "1rem 0",
        }}
      >
        <input
          type="checkbox"
          checked={showTechnicalDetails}
          onChange={(event) => setShowTechnicalDetails(event.target.checked)}
        />
        Show technical details
      </label>

      <div className="panel" style={{ padding: 0, overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: "0.85rem",
          }}
        >
          <thead>
            <tr
              style={{
                textAlign: "left",
                borderBottom: "1px solid var(--line)",
              }}
            >
              <th style={{ padding: "0.6rem" }}>Source field</th>
              <th style={{ padding: "0.6rem" }}>Inferred type</th>
              <th style={{ padding: "0.6rem" }}>Proposed business concept</th>
              <th style={{ padding: "0.6rem" }}>Confidence</th>
              <th style={{ padding: "0.6rem" }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {mappingDefinitions.map((mapping) => {
              const key = `${mapping.sourceDataset}:${mapping.sourceField}`;
              return (
                <tr key={key} style={{ borderBottom: "1px solid var(--line)" }}>
                  <td style={{ padding: "0.6rem" }}>
                    <strong>{mapping.sourceField}</strong>
                    <br />
                    <span style={{ color: "var(--muted)" }}>
                      {mapping.sourceDataset}
                    </span>
                  </td>
                  <td style={{ padding: "0.6rem" }}>{mapping.inferredType}</td>
                  <td style={{ padding: "0.6rem" }}>
                    {mapping.businessConcept}
                    {showTechnicalDetails && (
                      <>
                        <br />
                        <span
                          style={{ color: "var(--muted)", fontSize: "0.78rem" }}
                        >
                          {mapping.technicalNote}
                        </span>
                      </>
                    )}
                  </td>
                  <td style={{ padding: "0.6rem" }}>
                    {Math.round(mapping.confidence * 100)}%
                  </td>
                  <td style={{ padding: "0.6rem" }}>
                    <label
                      style={{
                        display: "inline-flex",
                        gap: "0.4rem",
                        alignItems: "center",
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={accepted[key]}
                        onChange={(event) =>
                          setAccepted((prev) => ({
                            ...prev,
                            [key]: event.target.checked,
                          }))
                        }
                      />
                      {accepted[key] ? "Accepted" : "Changed"}
                    </label>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <button
        type="button"
        onClick={onBuildOntology}
        style={{ marginTop: "1.5rem" }}
      >
        Build Ontology
      </button>
    </section>
  );
}
