"use client";
import { useRef, useState } from "react";
import { supplierRiskApi } from "@/lib/supplier-risk/api-client";
import type { ReplayOption } from "@/lib/supplier-risk/contracts";
export function ReplayDialog({
  logicalId,
  options,
  onAccepted,
}: {
  logicalId: string;
  options: ReplayOption[];
  onAccepted: () => void;
}) {
  const eligible = options.filter((o) => o.eligible);
  const dialog = useRef<HTMLDialogElement>(null);
  const [selected, setSelected] = useState(eligible[0]?.option_reference ?? "");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit() {
    const option = eligible.find((o) => o.option_reference === selected);
    if (!option) return;
    setBusy(true);
    const request = crypto.randomUUID();
    try {
      await supplierRiskApi.replay(
        logicalId,
        {
          request_identifier: request,
          correlation_identifier: crypto.randomUUID(),
          reason,
          replay_option_reference: option.option_reference,
          expected_revision: option.revision,
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
        className="secondary"
        disabled={!eligible.length}
        onClick={() => dialog.current?.showModal()}
      >
        Privileged replay
      </button>
      <dialog ref={dialog} aria-labelledby="replay-title">
        <h2 id="replay-title">Replay from verified checkpoint</h2>
        <p>The original attempt will not be overwritten.</p>
        <label>
          Server-authorized checkpoint
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            {eligible.map((o) => (
              <option key={o.option_reference} value={o.option_reference}>
                {o.stage_label} · {new Date(o.checkpoint_at).toLocaleString()}
              </option>
            ))}
          </select>
        </label>
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
            Confirm privileged replay
          </button>
        </div>
      </dialog>
    </>
  );
}
