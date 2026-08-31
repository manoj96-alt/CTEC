// CDD-045 §16/§29 UI Truth Table: the three Reliance counts are the OQI
// hero semantic. No score, no percentage, no weighted composite -- three
// governed counts, rendered with equal visual weight so that UNKNOWN never
// reads as a quieter, safer variant of AT_RISK (CDD-045 §14/§19).
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
    color: string;
  }[] = [
    {
      key: "supported",
      label: "Reliance Supported",
      count: supported,
      color: "#1a7f37",
    },
    {
      key: "at-risk",
      label: "Reliance At Risk",
      count: atRisk,
      color: "#b42318",
    },
    {
      key: "unknown",
      label: "Reliance Unknown",
      count: unknown,
      color: "#7a5c00",
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
          <span
            aria-hidden="true"
            style={{
              display: "inline-block",
              width: "0.6rem",
              height: "0.6rem",
              borderRadius: "999px",
              backgroundColor: cell.color,
            }}
          />
          <span style={{ fontSize: "1.75rem", fontWeight: 700, lineHeight: 1 }}>
            {cell.count}
          </span>
          <span className="eyebrow">{cell.label}</span>
        </div>
      ))}
    </div>
  );
}
