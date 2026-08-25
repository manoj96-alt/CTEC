// Renders CDD-033 §7's capability-status taxonomy truthfully and
// consistently everywhere it is used. Deliberately has no variant for
// "NOT SUPPORTED / MUST NOT APPEAR" -- that category means the capability
// is omitted from the UI entirely, not badged (CDD-033 §7).
export type CapabilityStatus =
  | "SUPPORTED_NOW"
  | "SUPPORTED_BUT_UI_MISSING"
  | "AVAILABLE_BUT_DISCONNECTED"
  | "PLANNED"
  | "FUTURE_GATE";

const STATUS_LABEL: Record<CapabilityStatus, string> = {
  SUPPORTED_NOW: "Supported now",
  SUPPORTED_BUT_UI_MISSING: "Supported, UI pending",
  AVAILABLE_BUT_DISCONNECTED: "Available, not yet connected",
  PLANNED: "Planned",
  FUTURE_GATE: "Future capability",
};

export function CapabilityStatusBadge({
  status,
}: {
  status: CapabilityStatus;
}) {
  return (
    <span
      className="capability-status-badge"
      data-status={status}
      style={{
        display: "inline-block",
        fontSize: "0.75rem",
        fontWeight: 700,
        letterSpacing: "0.02em",
        textTransform: "uppercase",
        padding: "0.15rem 0.5rem",
        borderRadius: "999px",
        border: "1px solid var(--line)",
        color: "var(--muted)",
      }}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}
