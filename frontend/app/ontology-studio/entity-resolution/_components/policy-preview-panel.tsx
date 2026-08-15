"use client";

import { useState } from "react";
import {
  EntityResolutionApiError,
  entityResolutionApi,
} from "@/lib/entity-resolution/api-client";
import type {
  PolicySummary,
  PreviewResult,
} from "@/lib/entity-resolution/contracts";

type PreviewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; result: PreviewResult };

export function PolicyPreviewPanel({
  understandingKey,
  policies,
  selectedPolicyId,
  onSelectedPolicyIdChange,
}: {
  understandingKey: string;
  policies: PolicySummary[];
  selectedPolicyId: string;
  onSelectedPolicyIdChange: (policyId: string) => void;
}) {
  const [previewState, setPreviewState] = useState<PreviewState>({
    status: "idle",
  });

  if (policies.length === 0) {
    return (
      <div className="panel">
        <p style={{ fontWeight: 700 }}>No policies are available yet</p>
        <p style={{ color: "var(--muted)" }}>
          No resolution policy has been materialized for this tenant.
        </p>
      </div>
    );
  }

  async function runPreview() {
    if (!selectedPolicyId) return;
    setPreviewState({ status: "loading" });
    try {
      const result = await entityResolutionApi.preview(
        understandingKey,
        selectedPolicyId,
      );
      setPreviewState({ status: "ready", result });
    } catch (error) {
      const message =
        error instanceof EntityResolutionApiError
          ? error.problem.message
          : "The policy preview could not be computed.";
      setPreviewState({ status: "error", message });
    }
  }

  return (
    <section className="panel" aria-label="Policy preview">
      <h3>Policy</h3>
      <p style={{ color: "var(--muted)" }}>
        Choose a policy and preview its simulated outcome before deciding —
        previewing never changes anything. Deciding applies the policy selected
        here.
      </p>
      <div className="form-grid">
        <label>
          Policy
          <select
            value={selectedPolicyId}
            onChange={(e) => {
              onSelectedPolicyIdChange(e.target.value);
              setPreviewState({ status: "idle" });
            }}
          >
            {policies.map((policy) => (
              <option key={policy.policy_id} value={policy.policy_id}>
                {policy.policy_name} ({policy.policy_version})
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="action-row" style={{ marginTop: "1rem" }}>
        <button
          type="button"
          className="secondary"
          disabled={previewState.status === "loading" || !selectedPolicyId}
          onClick={() => void runPreview()}
        >
          {previewState.status === "loading"
            ? "Simulating…"
            : "Preview outcome"}
        </button>
      </div>
      {previewState.status === "error" && (
        <div className="error-summary" role="alert">
          {previewState.message}
        </div>
      )}
      {previewState.status === "ready" && (
        <dl className="status-grid" style={{ marginTop: "1rem" }}>
          <div>
            <dt>Simulated outcome</dt>
            <dd>{previewState.result.outcome}</dd>
          </div>
          <div>
            <dt>Confidence</dt>
            <dd>{previewState.result.business_confidence}</dd>
          </div>
          <div>
            <dt>Would change outcome?</dt>
            <dd>{previewState.result.would_change_outcome ? "Yes" : "No"}</dd>
          </div>
        </dl>
      )}
    </section>
  );
}
