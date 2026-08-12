"use client";

import type { CatalogEntry } from "@/lib/demo/dataset-catalog";
import type { ParsedFile } from "@/lib/demo/types";

export interface DatasetInspectionPanelProps {
  entry: CatalogEntry;
  parsedFile: ParsedFile<unknown>;
}

const ROLE_LABEL: Record<string, string> = {
  primary_key: "Primary key",
  foreign_key: "Foreign key",
  attribute: "Attribute",
};

function roleLabel(column: {
  role: string;
  relationshipTarget?: string;
  isPrimaryKey?: boolean;
}): string {
  const foreignKeySuffix = column.relationshipTarget
    ? ` → ${column.relationshipTarget}`
    : "";
  if (column.isPrimaryKey && column.role === "foreign_key") {
    return `Primary key · Foreign key${foreignKeySuffix}`;
  }
  return `${ROLE_LABEL[column.role]}${column.role === "foreign_key" ? foreignKeySuffix : ""}`;
}

export function DatasetInspectionPanel({
  entry,
  parsedFile,
}: DatasetInspectionPanelProps) {
  return (
    <div
      id="dataset-inspection-panel"
      className="panel"
      aria-label="Selected dataset details"
    >
      {/* Restrained live region: only this heading announces the change,
          nothing here receives programmatic focus. */}
      <h2 aria-live="polite" style={{ marginTop: 0 }}>
        {entry.businessName}{" "}
        <span style={{ color: "var(--muted)", fontWeight: 400 }}>
          ({entry.fileName})
        </span>
      </h2>

      <p className="eyebrow">Curated Sample Dataset metadata</p>
      <div className="dataset-table-wrap">
        <table>
          <caption className="sr-only">
            Schema for {entry.fileName}, curated for this demo
          </caption>
          <thead>
            <tr>
              <th scope="col">Field</th>
              <th scope="col">Type</th>
              <th scope="col">Required</th>
              <th scope="col">Role</th>
            </tr>
          </thead>
          <tbody>
            {entry.columns.map((column) => (
              <tr key={column.field}>
                <td>{column.field}</td>
                <td>{column.displayType}</td>
                <td>{column.required ? "Yes" : "No"}</td>
                <td>{roleLabel(column)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p
        style={{
          fontSize: "0.78rem",
          color: "var(--muted)",
          marginTop: "0.5rem",
        }}
      >
        Detected in file: {parsedFile.columns.join(", ")}
      </p>

      <p className="eyebrow" style={{ marginTop: "1.5rem" }}>
        Sample records
      </p>
      <div className="dataset-table-wrap">
        <table>
          <caption className="sr-only">
            Sample records from {entry.fileName}
          </caption>
          <thead>
            <tr>
              {parsedFile.columns.map((column) => (
                <th key={column} scope="col">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {parsedFile.sampleRows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {parsedFile.columns.map((column) => (
                  <td key={column}>{row[column]}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
