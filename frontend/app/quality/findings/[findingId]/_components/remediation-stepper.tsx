import type { RemediationResponse } from "@/lib/oqi/contracts";

// CDD-045 §20/§28 + OQI-UX companion §5: the explicit remediation lifecycle
// stepper CDD-045 always required. Purely presentational -- renders exactly
// the server's own case_status (plus authorization.status for the rejected
// composite state below), never derives, advances, or infers lifecycle
// state on its own.
const LINEAR_STEPS: { status: string; label: string }[] = [
  { status: "CANDIDATE_READY", label: "Candidate Ready" },
  { status: "AWAITING_AUTHORITY", label: "Awaiting Human Authorization" },
  { status: "AUTHORIZED", label: "Authorized" },
  { status: "EXTERNAL_EXECUTION_REPORTED", label: "Externally Reported" },
  { status: "AWAITING_REEVALUATION", label: "Awaiting Re-evaluation" },
  { status: "RESOLVED", label: "Resolved" },
];

const SIDE_STATE_LABEL: Record<string, string> = {
  STEWARD_INVESTIGATION: "Steward Investigation",
  NO_REMEDIATION: "No Remediation",
};

export function RemediationStepper({
  remediation,
}: {
  remediation: RemediationResponse;
}) {
  const caseStatus = remediation.case_status;
  if (!caseStatus) return null;

  // Rejection lives on authorization.status, never on case_status itself
  // (reject() never mutates the case) -- rendering plain
  // "Awaiting Human Authorization" here would misrepresent an
  // already-decided case as still pending.
  const isRejected =
    caseStatus === "AWAITING_AUTHORITY" &&
    remediation.authorization?.status === "REJECTED";

  if (isRejected) {
    return (
      <div role="group" aria-label="Remediation lifecycle">
        <span className="eyebrow">Remediation Lifecycle</span>
        <p style={{ fontWeight: 700 }}>Rejected</p>
      </div>
    );
  }

  if (caseStatus in SIDE_STATE_LABEL) {
    return (
      <div role="group" aria-label="Remediation lifecycle">
        <span className="eyebrow">Remediation Lifecycle</span>
        <p style={{ fontWeight: 700 }}>{SIDE_STATE_LABEL[caseStatus]}</p>
      </div>
    );
  }

  const currentIndex = LINEAR_STEPS.findIndex(
    (step) => step.status === caseStatus,
  );

  return (
    <div role="group" aria-label="Remediation lifecycle">
      <span className="eyebrow">Remediation Lifecycle</span>
      <ol className="stepper-list">
        {LINEAR_STEPS.map((step, index) => {
          const isCurrent = index === currentIndex;
          const isPast = currentIndex >= 0 && index < currentIndex;
          const variant = isCurrent ? "current" : isPast ? "past" : "future";
          return (
            <li
              key={step.status}
              aria-current={isCurrent ? "step" : undefined}
              className={`stepper-step stepper-step--${variant}`}
            >
              <span className="stepper-marker" aria-hidden="true" />
              {step.label}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
