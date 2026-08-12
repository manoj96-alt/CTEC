"use client";

import type { CatalogEntry } from "@/lib/demo/dataset-catalog";
import type { ParsedFile } from "@/lib/demo/types";

export interface DatasetFileCardProps {
  entry: CatalogEntry;
  parsedFile: ParsedFile<unknown>;
  issueCount: number;
  selected: boolean;
  onSelect: () => void;
}

export function DatasetFileCard({
  entry,
  parsedFile,
  issueCount,
  selected,
  onSelect,
}: DatasetFileCardProps) {
  const foreignKeys = entry.columns.filter((c) => c.role === "foreign_key");

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      aria-controls="dataset-inspection-panel"
      className="panel"
      style={{
        margin: 0,
        textAlign: "left",
        display: "block",
        width: "100%",
        cursor: "pointer",
        borderColor: selected ? "var(--accent)" : "var(--line)",
        boxShadow: selected
          ? "0 0 0 2px var(--accent)"
          : "0 12px 35px rgba(20, 33, 61, 0.05)",
      }}
    >
      <p style={{ fontWeight: 700, marginBottom: "0.15rem" }}>
        {entry.businessName}
      </p>
      <p
        style={{
          fontSize: "0.78rem",
          color: "var(--muted)",
          marginBottom: "0.5rem",
        }}
      >
        {entry.fileName}
      </p>
      <p style={{ fontSize: "0.85rem", marginBottom: "0.6rem" }}>
        {entry.purpose}
      </p>
      <p style={{ fontSize: "0.8rem", color: "var(--muted)", margin: 0 }}>
        {parsedFile.records.length} record
        {parsedFile.records.length === 1 ? "" : "s"} ·{" "}
        {parsedFile.columns.length} column
        {parsedFile.columns.length === 1 ? "" : "s"}
      </p>
      <p
        style={{
          fontSize: "0.8rem",
          color: "var(--muted)",
          margin: "0.2rem 0",
        }}
      >
        Primary key: {entry.primaryKey}
      </p>
      {foreignKeys.length > 0 && (
        <p
          style={{
            fontSize: "0.8rem",
            color: "var(--muted)",
            margin: "0.2rem 0",
          }}
        >
          References:{" "}
          {foreignKeys.map((fk) => fk.relationshipTarget).join(", ")}
        </p>
      )}
      <p
        style={{
          fontSize: "0.85rem",
          marginTop: "0.5rem",
          color: issueCount > 0 ? "var(--danger)" : "var(--success)",
        }}
      >
        {issueCount > 0
          ? `✗ ${issueCount} integrity issue${issueCount === 1 ? "" : "s"} detected`
          : "✓ No detected integrity issues"}
      </p>
    </button>
  );
}
