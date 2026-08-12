"use client";

export interface DecisionHistoryEntry {
  id: string;
  decision: "Approved" | "Rejected";
  user: string;
  timestamp: string;
  recommendationSummary: string;
  allocationPct: number;
  comment: string;
  evidenceReference: string;
}

export interface DecisionHistoryProps {
  entries: DecisionHistoryEntry[];
}

export function DecisionHistory({ entries }: DecisionHistoryProps) {
  if (entries.length === 0) return null;

  return (
    <div
      className="panel"
      style={{ padding: "1rem", marginTop: "1.5rem" }}
      data-testid="decision-history"
    >
      <p style={{ fontWeight: 700, marginBottom: "0.25rem" }}>
        Decision history
      </p>
      <p
        style={{
          fontSize: "0.78rem",
          color: "var(--muted)",
          marginTop: 0,
          marginBottom: "0.75rem",
        }}
      >
        Recorded locally for this demo session. Not production-grade immutable
        persistence.
      </p>
      <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
        {entries.map((entry) => (
          <li
            key={entry.id}
            style={{
              borderTop: "1px solid var(--line)",
              padding: "0.75rem 0",
              fontSize: "0.85rem",
            }}
          >
            <span
              style={{
                fontWeight: 700,
                color:
                  entry.decision === "Approved"
                    ? "var(--success)"
                    : "var(--danger)",
              }}
            >
              {entry.decision}
            </span>{" "}
            by {entry.user} · {entry.timestamp}
            <p style={{ margin: "0.35rem 0" }}>{entry.recommendationSummary}</p>
            <p style={{ margin: "0.15rem 0", color: "var(--muted)" }}>
              Allocation: {entry.allocationPct}% · Evidence:{" "}
              {entry.evidenceReference}
            </p>
            {entry.comment && (
              <p style={{ margin: "0.15rem 0", color: "var(--muted)" }}>
                Comment: {entry.comment}
              </p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
