"use client";
import { useRef, useState } from "react";
import { supplierRiskApi } from "@/lib/supplier-risk/api-client";
import type { RetryEligibility } from "@/lib/supplier-risk/contracts";
export function RetryDialog({
  logicalId,
  eligibility,
  onAccepted,
}: {
  logicalId: string;
  eligibility: RetryEligibility;
  onAccepted: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit() {
    setBusy(true);
    const request = crypto.randomUUID();
    try {
      await supplierRiskApi.retry(
        logicalId,
        {
          request_identifier: request,
          correlation_identifier: crypto.randomUUID(),
          reason,
          expected_revision: eligibility.revision,
        },
        request,
      );
      dialog.current?.close();
      onAccepted();
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <button
        disabled={!eligibility.eligible}
        onClick={() => dialog.current?.showModal()}
      >
        Request retry
      </button>
      <dialog ref={dialog} aria-labelledby="retry-title">
        <h2 id="retry-title">Retry failed attempt</h2>
        <p>The logical execution and original attempt remain in history.</p>
        <label>
          Reason
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            minLength={3}
            required
          />
        </label>
        <div className="dialog-actions">
          <button onClick={() => dialog.current?.close()}>Cancel</button>
          <button disabled={busy || reason.trim().length < 3} onClick={submit}>
            Confirm retry
          </button>
        </div>
      </dialog>
    </>
  );
}
