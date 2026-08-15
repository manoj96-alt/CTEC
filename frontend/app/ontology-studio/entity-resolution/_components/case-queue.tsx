"use client";

import type {
  CaseSummary,
  ResolutionOutcome,
} from "@/lib/entity-resolution/contracts";

export type OutcomeFilter = "all" | ResolutionOutcome;

const FILTERS: { label: string; value: OutcomeFilter }[] = [
  { label: "All", value: "all" },
  { label: "Possible", value: "Possible Resolution" },
  { label: "Unresolved", value: "Unresolved" },
  { label: "Blocked Conflict", value: "Blocked Conflict" },
];

function formatDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString();
}

export function CaseQueue({
  items,
  outcomeFilter,
  onOutcomeFilterChange,
  selectedKey,
  onSelect,
}: {
  items: CaseSummary[];
  outcomeFilter: OutcomeFilter;
  onOutcomeFilterChange: (value: OutcomeFilter) => void;
  selectedKey: string | null;
  onSelect: (understandingKey: string) => void;
}) {
  return (
    <section className="panel" aria-label="Resolution case queue">
      <div
        role="tablist"
        aria-label="Filter by outcome"
        style={{
          display: "flex",
          gap: "0.5rem",
          flexWrap: "wrap",
          marginBottom: "1rem",
        }}
      >
        {FILTERS.map((filter) => (
          <button
            key={filter.value}
            type="button"
            role="tab"
            aria-selected={outcomeFilter === filter.value}
            className={outcomeFilter === filter.value ? "button" : "secondary"}
            onClick={() => onOutcomeFilterChange(filter.value)}
          >
            {filter.label}
          </button>
        ))}
      </div>
      {items.length === 0 ? (
        <div className="empty">
          <p style={{ fontWeight: 700 }}>No cases in this queue</p>
          <p style={{ color: "var(--muted)" }}>
            There are no resolution cases matching this filter right now.
          </p>
        </div>
      ) : (
        <ul className="record-list">
          {items.map((item) => (
            <li key={item.record_id}>
              <button
                type="button"
                className="secondary"
                aria-current={selectedKey === item.understanding_key}
                style={{
                  width: "100%",
                  textAlign: "left",
                  display: "grid",
                  gridTemplateColumns: "1fr auto",
                  gap: "0.25rem",
                  border:
                    selectedKey === item.understanding_key
                      ? "2px solid var(--accent)"
                      : "1px solid var(--line)",
                }}
                onClick={() => onSelect(item.understanding_key)}
              >
                <strong>
                  {item.candidate_enterprise_entity_name ??
                    "No candidate attached"}
                </strong>
                <span>{item.outcome}</span>
                <small style={{ color: "var(--muted)" }}>
                  Confidence: {item.business_confidence} · Policy{" "}
                  {item.policy_version} · {item.supporting_source_object_count}{" "}
                  source record(s)
                </small>
                <small style={{ color: "var(--muted)" }}>
                  {formatDate(item.produced_at)}
                </small>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
