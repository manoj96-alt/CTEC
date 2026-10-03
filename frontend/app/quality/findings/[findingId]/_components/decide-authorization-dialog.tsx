"use client";

import { useRef, useState } from "react";
import { OqiApiError, oqiApi } from "@/lib/oqi/api-client";

// CDD-045 companion §M/§4 -- mirrors the existing entity-resolution
// decision-dialog.tsx native-<dialog> pattern. decided_by is never sent by
// this client at all (NOETVA-GOVERNED-AUTHORITY-BINDING-I-R1): the decision
// actor identity is bound exclusively, server-side, to the authenticated
// principal that made the HTTP call -- a client-asserted identity (from the
// ID token's `sub` or anywhere else) is not a trustworthy security boundary,
// since it is audience-pairwise and does not match the backend's own
// access-token-derived principal id for the same real user. This dialog
// only ever asserts the decision (approve/reject), never who is deciding.
// Approve means human authorization only -- never remediate/execute/resolve.
const ERROR_COPY: Record<string, string> = {
  REMEDIATION_SELF_APPROVAL_PROHIBITED:
    "The signed-in principal requested this authorization and cannot also decide it.",
  REMEDIATION_AUTHORIZATION_NOT_PENDING:
    "This authorization is no longer pending a decision.",
};

export function DecideAuthorizationDialog({
  authorizationId,
  instruction,
  disabled,
  onDecided,
}: {
  authorizationId: string;
  instruction: string;
  disabled?: boolean;
  onDecided: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [approve, setApprove] = useState(true);
  const [rejectionReason, setRejectionReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function openDialog() {
    setApprove(true);
    setRejectionReason("");
    setError(null);
    dialog.current?.showModal();
  }

  async function submit() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await oqiApi.decideAuthorization(authorizationId, {
        approve,
        rejection_reason: approve ? undefined : rejectionReason || undefined,
      });
      dialog.current?.close();
      onDecided();
    } catch (caught) {
      if (caught instanceof OqiApiError) {
        setError(
          ERROR_COPY[caught.code] ??
            `The decision could not be recorded (${caught.code}).`,
        );
      } else {
        setError("The decision could not be recorded.");
      }
    } finally {
      setBusy(false);
    }
  }

  const titleId = "decide-authorization-title";

  return (
    <>
      <button
        type="button"
        className="button"
        disabled={disabled}
        onClick={openDialog}
      >
        Decide Authorization
      </button>
      <dialog ref={dialog} aria-labelledby={titleId}>
        <h2 id={titleId}>Human Authorization</h2>
        <p style={{ color: "var(--muted)" }}>
          This authorizes the proposed remediation instruction below. It does
          not execute it, and it does not resolve the underlying Finding.
        </p>
        <p>
          <strong>Proposed instruction:</strong> {instruction}
        </p>

        <fieldset>
          <legend>Decision</legend>
          <label>
            <input
              type="radio"
              name="decision"
              checked={approve}
              onChange={() => setApprove(true)}
            />
            Approve
          </label>
          <label>
            <input
              type="radio"
              name="decision"
              checked={!approve}
              onChange={() => setApprove(false)}
            />
            Reject
          </label>
        </fieldset>

        {!approve ? (
          <label>
            Rejection reason (optional)
            <textarea
              value={rejectionReason}
              onChange={(event) => setRejectionReason(event.target.value)}
              placeholder="Explain why this authorization is being rejected…"
            />
          </label>
        ) : null}

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
            {busy
              ? "Recording…"
              : approve
                ? "Confirm: Approve"
                : "Confirm: Reject"}
          </button>
        </div>
      </dialog>
    </>
  );
}
