"use client";

import type { EvidenceItem, EvidenceProfile } from "@/lib/entity-resolution/contracts";

const CLASSIFICATION_ORDER = ["Veto", "Negative", "Positive", "Missing"] as const;

const CLASSIFICATION_LABEL: Record<string, string> = {
  Veto: "Veto (blocks resolution)",
  Negative: "Conflicts",
  Positive: "Agrees",
  Missing: "Not provided",
};

function groupByClassification(items: EvidenceItem[]): Map<string, EvidenceItem[]> {
  const groups = new Map<string, EvidenceItem[]>();
  for (const classification of CLASSIFICATION_ORDER) groups.set(classification, []);
  for (const item of items) {
    const bucket = groups.get(item.classification) ?? [];
    bucket.push(item);
    groups.set(item.classification, bucket);
  }
  return groups;
}

export function EvidenceList({ profile }: { profile: EvidenceProfile | null }) {
  if (!profile) {
    return (
      <div className="panel">
        <p style={{ fontWeight: 700 }}>No evidence profile is available</p>
        <p style={{ color: "var(--muted)" }}>
          This case was produced by the automated name-only resolution path
          and has no multi-attribute evidence to review.
        </p>
      </div>
    );
  }

  const groups = groupByClassification(profile.items);

  return (
    <section className="panel" aria-label="Evidence by category">
      <h3>Evidence by category</h3>
      {CLASSIFICATION_ORDER.map((classification) => {
        const items = groups.get(classification) ?? [];
        if (items.length === 0) return null;
        return (
          <div key={classification} style={{ marginTop: "1rem" }}>
            <p className="eyebrow">{CLASSIFICATION_LABEL[classification]}</p>
            <ul className="record-list">
              {items.map((item) => (
                <li key={`${item.evidence_type}-${item.compared_attributes.join(",")}`}>
                  <strong>{item.evidence_type}</strong>
                  <span>
                    {item.normalized_values.length > 0
                      ? item.normalized_values.join(", ")
                      : "—"}
                  </span>
                  <small style={{ color: "var(--muted)" }}>
                    {item.explanation}
                  </small>
                  <small style={{ color: "var(--muted)" }}>
                    Sources: {item.provenance}
                  </small>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </section>
  );
}
