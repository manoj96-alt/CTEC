import type { EvidenceStep } from "@/lib/ontology-copilot/contracts";

export function EvidencePath({ steps }: { steps: EvidenceStep[] }) {
  return (
    <ol className="record-list" aria-label="Evidence path">
      {steps.map((step) => (
        <li key={step.step}>
          <strong>{step.entity_name}</strong>{" "}
          <span style={{ color: "var(--muted)" }}>({step.entity_type_name})</span>
          {step.relationship_name && (
            <div style={{ color: "var(--muted)", fontSize: "0.85em" }}>
              ↓ {step.relationship_name}
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}
