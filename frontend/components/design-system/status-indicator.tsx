// CDD-079 (WOW-I1) §10: a third, distinct semantic vocabulary --
// describes the state of a specific piece of governed data/evidence.
// Deliberately separate from two other, pre-existing vocabularies this
// component must never be confused with or merged into:
//   - CapabilityStatus (capability-status-badge.tsx, untouched by this
//     phase) answers "is this feature exposed in this build."
//   - The OQI governed-lifecycle stage states (NOT_INVOKED,
//     NOT_EXERCISED, NOT_APPLICABLE, NOT_RESOLVED, ...) describe one
//     finding's remediation progress and are owned by WOW-I3.
// Every state renders label + shape + color together -- never color
// alone (CDD-079 §10/§25).
export type ObservatoryStatus =
  | "verified"
  | "conflict"
  | "attention"
  | "pending"
  | "unknown"
  | "deferred"
  | "not-invoked"
  | "not-exercised"
  | "unavailable"
  | "error";

const STATUS_LABEL: Record<ObservatoryStatus, string> = {
  verified: "Verified",
  conflict: "Conflict",
  attention: "Attention",
  pending: "Pending",
  unknown: "Unknown",
  deferred: "Deferred",
  "not-invoked": "Not invoked",
  "not-exercised": "Not exercised",
  unavailable: "Unavailable",
  error: "Error",
};

const STATUS_COLOR: Record<ObservatoryStatus, string> = {
  verified: "var(--obs-verified)",
  conflict: "var(--obs-conflict)",
  attention: "var(--obs-attention)",
  pending: "var(--obs-pending)",
  unknown: "var(--obs-unknown)",
  deferred: "var(--obs-deferred)",
  "not-invoked": "var(--obs-unknown)",
  "not-exercised": "var(--obs-unknown)",
  unavailable: "var(--obs-deferred)",
  error: "var(--danger)",
};

// Distinct dot shapes so meaning never depends on color perception
// alone: a solid dot for a settled/known state, a ring for an
// unsettled/deferred/unknown one, a diamond for something requiring
// attention or in conflict.
const STATUS_SHAPE: Record<ObservatoryStatus, "solid" | "ring" | "diamond"> = {
  verified: "solid",
  conflict: "diamond",
  attention: "diamond",
  pending: "ring",
  unknown: "ring",
  deferred: "ring",
  "not-invoked": "ring",
  "not-exercised": "ring",
  unavailable: "ring",
  error: "diamond",
};

export function StatusIndicator({ status }: { status: ObservatoryStatus }) {
  const color = STATUS_COLOR[status];
  const shape = STATUS_SHAPE[status];
  return (
    <span className="obs-status-indicator" data-status={status}>
      <span
        className="obs-status-indicator-dot"
        aria-hidden="true"
        style={{
          borderRadius: shape === "diamond" ? "2px" : "50%",
          transform: shape === "diamond" ? "rotate(45deg)" : undefined,
          background: shape === "ring" ? "transparent" : color,
          border: shape === "ring" ? `2px solid ${color}` : undefined,
        }}
      />
      {STATUS_LABEL[status]}
    </span>
  );
}
