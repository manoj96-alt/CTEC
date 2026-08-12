"use client";

import type { DemoDataset } from "@/lib/demo/types";

export interface DatasetValidationSummaryProps {
  dataset: DemoDataset;
}

export function DatasetValidationSummary({
  dataset,
}: DatasetValidationSummaryProps) {
  const issueCount = dataset.validationIssues.length;

  return (
    <section className="panel">
      <p className="eyebrow">Dataset Validation</p>
      <p
        style={{
          fontWeight: 700,
          color: issueCount > 0 ? "var(--danger)" : "var(--success)",
          marginBottom: "0.5rem",
        }}
      >
        {issueCount > 0
          ? `✗ ${issueCount} integrity issue${issueCount === 1 ? "" : "s"} detected`
          : "✓ No detected integrity issues"}
      </p>

      {issueCount > 0 && (
        <ul
          style={{
            margin: "0 0 0.75rem",
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
      )}

      <p style={{ fontSize: "0.78rem", color: "var(--muted)", margin: 0 }}>
        Deterministic validation currently checks for duplicate identifiers and
        broken references. Other checks (missing columns, empty files, invalid
        numeric or status values) are a known limitation for a future
        enhancement.
      </p>
    </section>
  );
}
