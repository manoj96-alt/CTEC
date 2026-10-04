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
  // CDD-091 §3: no default decision -- null means neither Approve nor
  // Reject has been deliberately selected yet. Opening the dialog, or
  // clicking the primary CTA, must never imply an authorization choice
  // the user did not explicitly make.
  const [approve, setApprove] = useState<boolean | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // CDD-091 §4: set only when the server has returned exactly
  // REMEDIATION_SELF_APPROVAL_PROHIBITED for this authorization. Disabling
  // Approve here is a UX affordance only -- it never substitutes for the
  // server's own enforcement. A client that bypasses this control (e.g. by
  // editing the DOM or calling the API directly) still receives the same
  // server rejection on every attempt; nothing client-side is ever treated
  // as the authority that decides whether self-approval is allowed.
  const [selfApprovalBlocked, setSelfApprovalBlocked] = useState(false);

  function openDialog() {
    setApprove(null);
    setRejectionReason("");
    setError(null);
    setSelfApprovalBlocked(false);
    dialog.current?.showModal();
  }

  async function submit() {
    if (busy || approve === null) return;
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
        if (caught.code === "REMEDIATION_SELF_APPROVAL_PROHIBITED") {
          setSelfApprovalBlocked(true);
        }
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
          {/* CDD-091 §3/§9: `.decision-option` scopes the row layout to
              exactly these two labels -- the rejection-reason label below,
              and every other dialog label elsewhere, keep the existing
              stacked layout untouched. */}
          <label className="decision-option">
            <input
              type="radio"
              name="decision"
              checked={approve === true}
              disabled={selfApprovalBlocked}
              onChange={() => setApprove(true)}
            />
            Approve
          </label>
          <label className="decision-option">
            <input
              type="radio"
              name="decision"
              checked={approve === false}
              onChange={() => setApprove(false)}
            />
            Reject
          </label>
        </fieldset>

        {approve === false ? (
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
          <button
            type="button"
            disabled={
              busy ||
              approve === null ||
              (approve === true && selfApprovalBlocked)
            }
            onClick={() => void submit()}
          >
            {busy
              ? "Recording…"
              : approve === null
                ? "Confirm decision"
                : approve
                  ? "Confirm: Approve"
                  : "Confirm: Reject"}
          </button>
        </div>
      </dialog>
    </>
  );
}
