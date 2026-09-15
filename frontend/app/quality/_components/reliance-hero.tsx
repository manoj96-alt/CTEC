import {
  StatusIndicator,
  type ObservatoryStatus,
} from "@/components/design-system/status-indicator";

// CDD-045 §16/§29 UI Truth Table: the three Reliance counts are the OQI
// hero semantic. No score, no percentage, no weighted composite -- three
// governed counts, rendered with equal visual weight so that UNKNOWN never
// reads as a quieter, safer variant of AT_RISK (CDD-045 §14/§19).
//
// CDD-081 §2: the raw inline-hex dots are replaced with the real,
// governed StatusIndicator vocabulary (CDD-079 §10) -- the same
// verified/conflict/unknown mapping already shipped for the Overview
// spotlight's Reliance cells, reused here rather than reinvented.
export function RelianceHero({
  supported,
  atRisk,
  unknown,
}: {
  supported: number;
  atRisk: number;
  unknown: number;
}) {
  const cells: {
    key: string;
    label: string;
    count: number;
    status: ObservatoryStatus;
  }[] = [
    {
      key: "supported",
      label: "Reliance Supported",
      count: supported,
      status: "verified",
    },
    {
      key: "at-risk",
      label: "Reliance At Risk",
      count: atRisk,
      status: "conflict",
    },
    {
      key: "unknown",
      label: "Reliance Unknown",
      count: unknown,
      status: "unknown",
    },
  ];

  return (
    <div
      role="group"
      aria-label="Enterprise knowledge reliance"
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(11rem, 1fr))",
        gap: "1rem",
      }}
    >
      {cells.map((cell) => (
        <div
          key={cell.key}
          className="panel"
          style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}
        >
          <StatusIndicator status={cell.status} />
          <span style={{ fontSize: "1.75rem", fontWeight: 700, lineHeight: 1 }}>
            {cell.count}
          </span>
          <span className="eyebrow">{cell.label}</span>
        </div>
      ))}
    </div>
  );
}
