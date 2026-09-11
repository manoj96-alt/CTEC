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

// CDD-062 §5: five states, distinguishable by more than color alone --
// color + border style + opacity. Label text above is unchanged; only
// the presentation below varies by status. Deliberately does not use
// --accent (the product's primary interactive/action color, which would
// wrongly imply a badge is clickable/primary) or --danger (none of these
// five states is a failure).
const STATUS_PRESENTATION: Record<
  CapabilityStatus,
  { color: string; borderStyle: string; opacity: number }
> = {
  SUPPORTED_NOW: { color: "var(--success)", borderStyle: "solid", opacity: 1 },
  SUPPORTED_BUT_UI_MISSING: {
    color: "var(--attention)",
    borderStyle: "solid",
    opacity: 1,
  },
  AVAILABLE_BUT_DISCONNECTED: {
    color: "var(--pending)",
    borderStyle: "dashed",
    opacity: 1,
  },
  PLANNED: { color: "var(--muted)", borderStyle: "dotted", opacity: 1 },
  FUTURE_GATE: { color: "var(--muted)", borderStyle: "dotted", opacity: 0.7 },
};

export function CapabilityStatusBadge({
  status,
}: {
  status: CapabilityStatus;
}) {
  const presentation = STATUS_PRESENTATION[status];
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
        borderWidth: "1px",
        borderStyle: presentation.borderStyle,
        borderColor: presentation.color,
        color: presentation.color,
        opacity: presentation.opacity,
      }}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}
