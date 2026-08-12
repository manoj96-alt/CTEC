"use client";

import type { DemoDataset } from "@/lib/demo/types";

export interface ImportDataStageProps {
  dataset: DemoDataset | null;
  loading: boolean;
  error: string | null;
  onLoadSampleDataset: () => void;
  onContinue: () => void;
}

function fileCards(dataset: DemoDataset) {
  return [
    dataset.suppliers,
    dataset.materials,
    dataset.products,
    dataset.facilities,
    dataset.supplyAgreements,
    dataset.riskEvents,
    dataset.revenueExposure,
  ];
}

function issuesForFile(dataset: DemoDataset, fileName: string) {
  return dataset.validationIssues.filter((issue) => issue.file === fileName);
}

export function ImportDataStage({
  dataset,
  loading,
  error,
  onLoadSampleDataset,
  onContinue,
}: ImportDataStageProps) {
  return (
    <section>
      <p className="eyebrow">Stage 1 of 5</p>
      <h2 style={{ marginTop: "0.25rem" }}>Import Data</h2>
      <p style={{ color: "var(--muted)", maxWidth: "42rem" }}>
        This demo uses a small, deterministic sample dataset — seven connected
        source files covering suppliers, materials, products, facilities, supply
        agreements, risk events, and revenue exposure.
      </p>

      {!dataset && (
        <button type="button" onClick={onLoadSampleDataset} disabled={loading}>
          {loading ? "Loading sample dataset…" : "Load Sample Dataset"}
        </button>
      )}

      {error && (
        <p role="alert" style={{ color: "var(--danger)", marginTop: "1rem" }}>
          {error}
        </p>
      )}

      {dataset && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(19rem, 1fr))",
              gap: "1rem",
              marginTop: "1.5rem",
            }}
          >
            {fileCards(dataset).map((file) => {
              const fileIssues = issuesForFile(dataset, file.fileName);
              return (
                <div
                  key={file.fileName}
                  className="panel"
                  style={{ padding: "1rem" }}
                >
                  <p style={{ fontWeight: 700, marginBottom: "0.25rem" }}>
                    {file.fileName}
                  </p>
                  <p
                    style={{
                      color:
                        fileIssues.length > 0
                          ? "var(--danger)"
                          : "var(--success)",
                      fontSize: "0.85rem",
                      margin: 0,
                    }}
                  >
                    {fileIssues.length > 0
                      ? `✗ ${fileIssues.length} issue${fileIssues.length === 1 ? "" : "s"} found`
                      : `✓ Valid — ${file.records.length} row${file.records.length === 1 ? "" : "s"} detected`}
                  </p>
                  <p
                    style={{
                      color: "var(--muted)",
                      fontSize: "0.8rem",
                      marginTop: "0.5rem",
                    }}
                  >
                    Columns: {file.columns.join(", ")}
                  </p>
                  <table
                    style={{
                      width: "100%",
                      fontSize: "0.75rem",
                      marginTop: "0.5rem",
                    }}
                  >
                    <tbody>
                      {file.sampleRows.slice(0, 2).map((row, rowIndex) => (
                        <tr key={rowIndex}>
                          <td
                            style={{
                              color: "var(--muted)",
                              paddingRight: "0.5rem",
                            }}
                          >
                            {Object.values(row)[0]}
                          </td>
                          <td style={{ color: "var(--muted)" }}>
                            {Object.values(row)[1]}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              );
            })}
          </div>

          {dataset.validationIssues.length > 0 && (
            <div
              className="panel"
              style={{
                padding: "1rem",
                marginTop: "1.5rem",
                borderColor: "var(--danger)",
              }}
              role="alert"
              data-testid="validation-issues"
            >
              <p
                style={{
                  fontWeight: 700,
                  color: "var(--danger)",
                  marginBottom: "0.5rem",
                }}
              >
                {dataset.validationIssues.length} data integrity issue
                {dataset.validationIssues.length === 1 ? "" : "s"} found
              </p>
              <ul
                style={{
                  margin: 0,
                  paddingLeft: "1.2rem",
                  fontSize: "0.85rem",
                }}
              >
                {dataset.validationIssues.map((issue, index) => (
                  <li key={index}>
                    <strong>{issue.file}</strong> row {issue.rowIndex + 1} (
                    {issue.field}): {issue.message}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div
            className="panel"
            style={{ padding: "1rem", marginTop: "1.5rem" }}
          >
            <p style={{ fontWeight: 700, marginBottom: "0.5rem" }}>
              Relationship keys discovered
            </p>
            <ul
              style={{
                margin: 0,
                paddingLeft: "1.2rem",
                fontSize: "0.85rem",
                color: "var(--muted)",
              }}
            >
              {dataset.relationshipKeys.map((key) => (
                <li key={key.fieldName}>
                  {key.fieldName} — links {key.files.join(" ↔ ")}
                </li>
              ))}
            </ul>
          </div>

          <button
            type="button"
            onClick={onContinue}
            style={{ marginTop: "1.5rem" }}
          >
            Continue to Schema Mapping
          </button>
        </>
      )}
    </section>
  );
}
