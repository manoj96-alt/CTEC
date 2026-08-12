"use client";

import type { IncompleteScenario } from "@/lib/demo/scenario-facts";

export interface IncompleteEvidenceNoticeProps {
  resolution: IncompleteScenario;
  stageLabel: string;
}

export function IncompleteEvidenceNotice({
  resolution,
  stageLabel,
}: IncompleteEvidenceNoticeProps) {
  return (
    <section>
      <p className="eyebrow">{stageLabel}</p>
      <div
        className="panel"
        style={{
          padding: "1.25rem",
          marginTop: "0.75rem",
          borderColor: "var(--danger)",
        }}
        role="alert"
        data-testid="incomplete-evidence-notice"
      >
        <p
          style={{
            fontWeight: 700,
            color: "var(--danger)",
            marginBottom: "0.5rem",
          }}
        >
          Incomplete evidence — cannot proceed
        </p>
        <p style={{ margin: "0 0 0.5rem", fontSize: "0.9rem" }}>
          Broken relationship: <strong>{resolution.brokenRelationship}</strong>
        </p>
        <p style={{ margin: 0, fontSize: "0.9rem", color: "var(--muted)" }}>
          {resolution.reason}
        </p>
        <p
          style={{
            marginTop: "0.75rem",
            fontSize: "0.85rem",
            color: "var(--muted)",
          }}
        >
          This stage requires a complete, traceable path from imported source
          records through to a decision. Go back to Import Data or Map Schema to
          review the source files.
        </p>
      </div>
    </section>
  );
}
