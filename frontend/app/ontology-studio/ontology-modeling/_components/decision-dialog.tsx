"use client";

import { useRef, useState } from "react";
import {
  OntologyModelingApiError,
  ontologyModelingApi,
} from "@/lib/ontology-modeling/api-client";
import type { ProposalDetail } from "@/lib/ontology-modeling/contracts";

// Structurally mirrors entity-resolution/_components/decision-dialog.tsx:
// a <dialog> confirm per action, busy/error state, and a conflict prompt
// generalizing that file's own STALE_RESOLUTION_CASE UX pattern to Gate
// M's own fail-closed error codes. Approve/Publish carry no reason field
// (AA v1.1 §14, §16); Reject carries a bounded, optional reason (AA v1.1
// §15) -- the backend, not this component, is the authoritative length
// bound.
const MAX_REJECTION_REASON_LENGTH = 1000;

type Action = "approve" | "reject" | "publish";

const ACTION_LABEL: Record<Action, string> = {
  approve: "Approve",
  reject: "Reject",
  publish: "Publish",
};

function isAvailable(
  action: Action,
  status: ProposalDetail["status"],
): boolean {
  if (action === "approve" || action === "reject") return status === "Proposed";
  return status === "Approved";
}

function DecisionButton({
  action,
  proposal,
  onDecided,
}: {
  action: Action;
  proposal: ProposalDetail;
  onDecided: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);

  function openDialog() {
    setReason("");
    setError(null);
    setConflict(false);
    dialog.current?.showModal();
  }

  async function submit() {
    setBusy(true);
    setError(null);
    setConflict(false);
    try {
      const id = proposal.ontology_change_proposal_id;
      if (action === "approve") await ontologyModelingApi.approve(id);
      else if (action === "reject")
        await ontologyModelingApi.reject(id, {
          rejection_reason: reason || null,
        });
      else await ontologyModelingApi.publish(id);
      dialog.current?.close();
      onDecided();
    } catch (caught) {
      if (caught instanceof OntologyModelingApiError) {
        if (caught.status === 409) {
          setConflict(true);
        } else if (caught.status === 403) {
          setError("AUTHORIZATION_SCOPE_REQUIRED");
        } else {
          setError(caught.code);
        }
      } else {
        setError("The decision could not be recorded.");
      }
    } finally {
      setBusy(false);
    }
  }

  const titleId = `ontology-modeling-decision-${action}-${proposal.ontology_change_proposal_id}`;

  return (
    <>
      <button
        type="button"
        className={
          action === "approve" || action === "publish" ? "button" : "secondary"
        }
        disabled={!isAvailable(action, proposal.status)}
        onClick={openDialog}
      >
        {ACTION_LABEL[action]}
      </button>
      <dialog ref={dialog} aria-labelledby={titleId}>
        <h2 id={titleId}>{ACTION_LABEL[action]}</h2>
        {conflict ? (
          <div className="error-summary" role="alert">
            <p style={{ fontWeight: 700 }}>This proposal has changed</p>
            <p>
              Another authorized principal has already acted on this proposal,
              or its target name is no longer available in the governed
              ontology. Reload the proposal list to see the latest state before
              deciding.
            </p>
            <div className="dialog-actions">
              <button
                type="button"
                onClick={() => {
                  dialog.current?.close();
                  onDecided();
                }}
              >
                Reload proposals
              </button>
            </div>
          </div>
        ) : (
          <>
            {action === "reject" && (
              <label>
                Reason (optional)
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  maxLength={MAX_REJECTION_REASON_LENGTH}
                  placeholder="Explain why this proposal is being rejected…"
                />
              </label>
            )}
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
                disabled={busy}
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

export function DecisionDialog({
  proposal,
  onDecided,
}: {
  proposal: ProposalDetail;
  onDecided: () => void;
}) {
  return (
    <div style={{ display: "flex", gap: "0.5rem" }}>
      <DecisionButton
        action="approve"
        proposal={proposal}
        onDecided={onDecided}
      />
      <DecisionButton
        action="reject"
        proposal={proposal}
        onDecided={onDecided}
      />
      <DecisionButton
        action="publish"
        proposal={proposal}
        onDecided={onDecided}
      />
    </div>
  );
}
