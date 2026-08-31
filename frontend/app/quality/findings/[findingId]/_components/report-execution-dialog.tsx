"use client";

import { useRef, useState } from "react";
import { OqiApiError, oqiApi } from "@/lib/oqi/api-client";

// CDD-045 companion §N -- confirm-only interaction (the backend
// ReportExecutionRequest has zero fields, so no data-entry form is
// authorized). Reporting execution never implies CTEC wrote to the source
// system, and never implies the Finding is resolved -- both firewalls are
// stated explicitly in the confirmation copy itself, not only in a
// tooltip.
const ERROR_COPY: Record<string, string> = {
  REMEDIATION_ACTION_MISMATCH:
    "The Finding has changed since this remediation was authorized. This report cannot be recorded against a stale authorization.",
  REMEDIATION_AUTHORIZATION_ALREADY_CONSUMED:
    "Execution has already been reported for this authorization.",
};

export function ReportExecutionDialog({
  authorizationId,
  disabled,
  onReported,
}: {
  authorizationId: string;
  disabled?: boolean;
  onReported: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function openDialog() {
    setError(null);
    dialog.current?.showModal();
  }

  async function submit() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await oqiApi.reportExecution(authorizationId);
      dialog.current?.close();
      onReported();
    } catch (caught) {
      if (caught instanceof OqiApiError) {
        setError(
          ERROR_COPY[caught.code] ??
            `The report could not be recorded (${caught.code}).`,
        );
      } else {
        setError("The report could not be recorded.");
      }
    } finally {
      setBusy(false);
    }
  }

  const titleId = "report-execution-title";

  return (
    <>
      <button
        type="button"
        className="button"
        disabled={disabled}
        onClick={openDialog}
      >
        Report Execution
      </button>
      <dialog ref={dialog} aria-labelledby={titleId}>
        <h2 id={titleId}>Report Execution</h2>
        <p>
          I am reporting that the externally authorized remediation has been
          executed. CTEC does not perform this execution itself and does not
          write to the source system.
        </p>
        <p style={{ color: "var(--muted)" }}>
          This does not resolve the Finding. Resolution requires fresh evidence
          and re-evaluation.
        </p>

        {error && (
          <div className="error-summary" role="alert">
            {error}
          </div>
        )}

        <div className="dialog-actions">
          <button type="button" onClick={() => dialog.current?.close()}>
            Cancel
          </button>
          <button type="button" disabled={busy} onClick={() => void submit()}>
            {busy ? "Recording…" : "Confirm: Report Execution"}
          </button>
        </div>
      </dialog>
    </>
  );
}
