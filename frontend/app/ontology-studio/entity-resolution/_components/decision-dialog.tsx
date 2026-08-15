"use client";

import { useRef, useState } from "react";
import {
  EntityResolutionApiError,
  entityResolutionApi,
} from "@/lib/entity-resolution/api-client";
import type { StewardDecisionAction } from "@/lib/entity-resolution/contracts";

const ACTION_LABEL: Record<StewardDecisionAction, string> = {
  confirm_match: "Confirm match",
  reject_match: "Reject match",
  mark_unresolved: "Mark unresolved",
  block_conflict: "Block conflict",
};

const ACTION_DESCRIPTION: Record<StewardDecisionAction, string> = {
  confirm_match:
    "Resolves the case to the proposed candidate. Refused by the server if the evidence still contains an unresolved veto conflict.",
  reject_match:
    "Rejects the proposed candidate while keeping the case available for further review.",
  mark_unresolved: "Defers the case for later review, clearing any proposed candidate.",
  block_conflict:
    "Marks the case as a blocked conflict. Refused by the server unless the persisted evidence contains an applicable veto.",
};

export function DecisionDialog({
  action,
  understandingKey,
  policyId,
  basedOnRecordId,
  disabled,
  onDecided,
  onStale,
}: {
  action: StewardDecisionAction;
  understandingKey: string;
  policyId: string | null;
  basedOnRecordId: string;
  disabled?: boolean;
  onDecided: () => void;
  onStale: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [rationale, setRationale] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stale, setStale] = useState(false);

  function openDialog() {
    setRationale("");
    setError(null);
    setStale(false);
    dialog.current?.showModal();
  }

  async function submit() {
    if (!policyId || busy) return;
    setBusy(true);
    setError(null);
    setStale(false);
    try {
      await entityResolutionApi.decide(understandingKey, {
        action,
        rationale,
        based_on_record_id: basedOnRecordId,
        policy_id: policyId,
      });
      dialog.current?.close();
      onDecided();
    } catch (caught) {
      if (
        caught instanceof EntityResolutionApiError &&
        caught.problem.code === "STALE_RESOLUTION_CASE"
      ) {
        setStale(true);
      } else if (caught instanceof EntityResolutionApiError) {
        setError(caught.problem.message || caught.problem.code);
      } else {
        setError("The decision could not be recorded.");
      }
    } finally {
      setBusy(false);
    }
  }

  const titleId = `decision-title-${action}`;

  return (
    <>
      <button
        type="button"
        className={action === "confirm_match" ? "button" : "secondary"}
        disabled={disabled || !policyId}
        onClick={openDialog}
      >
        {ACTION_LABEL[action]}
      </button>
      <dialog ref={dialog} aria-labelledby={titleId}>
        <h2 id={titleId}>{ACTION_LABEL[action]}</h2>
        <p style={{ color: "var(--muted)" }}>{ACTION_DESCRIPTION[action]}</p>
        {stale ? (
          <div className="error-summary" role="alert">
            <p style={{ fontWeight: 700 }}>This case has been updated</p>
            <p>
              Another steward (or the automated engine) has already recorded a
              decision on this case since it was loaded. Reload the case to
              see the latest evidence before deciding.
            </p>
            <div className="dialog-actions">
              <button
                type="button"
                onClick={() => {
                  dialog.current?.close();
                  onStale();
                }}
              >
                Reload case
              </button>
            </div>
          </div>
        ) : (
          <>
            <label>
              Rationale
              <textarea
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
                minLength={10}
                required
                placeholder="Explain the basis for this decision…"
              />
            </label>
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
                disabled={busy || rationale.trim().length < 10}
                onClick={() => void submit()}
              >
                {busy ? "Recording…" : `Confirm: ${ACTION_LABEL[action]}`}
              </button>
            </div>
          </>
        )}
      </dialog>
    </>
  );
}
