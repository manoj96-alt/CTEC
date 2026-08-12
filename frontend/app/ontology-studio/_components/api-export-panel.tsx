"use client";

import { useState } from "react";

const ENDPOINTS = [
  { label: "Ontology endpoint", path: "/api/v1/ontologies/supplier-risk" },
  {
    label: "Version endpoint",
    path: "/api/v1/ontologies/supplier-risk/versions/1.0",
  },
  {
    label: "JSON-LD export endpoint",
    path: "/api/v1/ontologies/supplier-risk/export?format=json-ld",
  },
];

const INTEGRATION_PATTERNS = [
  {
    name: "Palantir",
    description:
      "Palantir can consume the published ontology, mappings and governed semantic features as input to its own models and operational workflows.",
  },
  {
    name: "Databricks",
    description:
      "Databricks pipelines can retrieve the published ontology and mappings to align lakehouse tables with governed concepts.",
  },
  {
    name: "Snowflake",
    description:
      "Snowflake consumers can retrieve the published ontology to map warehouse tables to governed concepts and relationships.",
  },
  {
    name: "MCP / AI agents",
    description:
      "An MCP-connected agent can retrieve the published ontology as grounded context before reasoning about supplier risk.",
  },
];

export function ApiExportPanel({
  preview,
  onCopy,
}: {
  preview: Record<string, unknown> | null;
  onCopy?: (text: string) => void;
}) {
  const [copied, setCopied] = useState<string | null>(null);

  const handleCopy = (text: string, label: string) => {
    if (onCopy) {
      onCopy(text);
    } else if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text).catch(() => undefined);
    }
    setCopied(label);
  };

  return (
    <section className="panel" style={{ marginTop: "1.5rem" }}>
      <p className="eyebrow">Ontology as a Service</p>
      <h2 style={{ marginTop: "0.25rem" }}>API &amp; Export</h2>

      <ul
        style={{
          marginTop: "1rem",
          paddingLeft: "1.2rem",
          fontSize: "0.85rem",
        }}
      >
        {ENDPOINTS.map((endpoint) => (
          <li key={endpoint.path} style={{ marginBottom: "0.5rem" }}>
            <code>{endpoint.path}</code>{" "}
            <button
              type="button"
              className="button"
              style={{
                fontSize: "0.7rem",
                padding: "0.15rem 0.5rem",
                marginLeft: "0.5rem",
              }}
              onClick={() => handleCopy(endpoint.path, endpoint.label)}
            >
              {copied === endpoint.label ? "Copied" : "Copy Endpoint"}
            </button>
          </li>
        ))}
      </ul>

      <p style={{ marginTop: "1rem", fontWeight: 700, fontSize: "0.85rem" }}>
        Live response preview (JSON-LD)
      </p>
      {preview ? (
        <pre
          style={{
            marginTop: "0.5rem",
            padding: "0.75rem",
            background: "var(--panel-alt, #f7f7f7)",
            borderRadius: "0.5rem",
            fontSize: "0.75rem",
            overflowX: "auto",
            maxHeight: "12rem",
          }}
        >
          {JSON.stringify(preview, null, 2)}
        </pre>
      ) : (
        <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
          Preview unavailable — the export endpoint could not be reached.
        </p>
      )}
      {preview && (
        <button
          type="button"
          className="button"
          style={{ marginTop: "0.5rem" }}
          onClick={() => handleCopy(JSON.stringify(preview, null, 2), "json")}
        >
          {copied === "json" ? "Copied" : "Copy JSON"}
        </button>
      )}

      <p style={{ marginTop: "1.5rem", fontWeight: 700, fontSize: "0.85rem" }}>
        External consumption
      </p>
      <div
        style={{
          marginTop: "0.5rem",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(14rem, 1fr))",
          gap: "0.75rem",
        }}
      >
        {INTEGRATION_PATTERNS.map((pattern) => (
          <div key={pattern.name} style={{ fontSize: "0.85rem" }}>
            <p style={{ fontWeight: 700 }}>
              {pattern.name}{" "}
              <span className="eyebrow">Integration pattern</span>
            </p>
            <p style={{ color: "var(--muted)" }}>{pattern.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
