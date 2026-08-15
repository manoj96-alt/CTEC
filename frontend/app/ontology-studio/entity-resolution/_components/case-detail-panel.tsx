"use client";

import { useCallback, useEffect, useState } from "react";
import {
  EntityResolutionApiError,
  entityResolutionApi,
} from "@/lib/entity-resolution/api-client";
import type {
  CaseDetail,
  PolicySummary,
  StewardDecisionAction,
} from "@/lib/entity-resolution/contracts";
import { DecisionDialog } from "./decision-dialog";
import { EvidenceList } from "./evidence-list";
import { PolicyPreviewPanel } from "./policy-preview-panel";

type DetailState =
  | { status: "loading" }
  | { status: "unauthorized" }
  | { status: "not-found" }
  | { status: "error"; message: string }
  | { status: "ready"; detail: CaseDetail };

type PoliciesState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; items: PolicySummary[] };

const ACTIONS: StewardDecisionAction[] = [
  "confirm_match",
  "reject_match",
  "mark_unresolved",
  "block_conflict",
];

function formatDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString();
}

export function CaseDetailPanel({
  understandingKey,
  onDecided,
  onClose,
}: {
  understandingKey: string;
  onDecided: () => void;
  onClose: () => void;
}) {
  const [detailState, setDetailState] = useState<DetailState>({
    status: "loading",
  });
  const [policiesState, setPoliciesState] = useState<PoliciesState>({
    status: "loading",
  });
  const [selectedPolicyId, setSelectedPolicyId] = useState("");
  const [reloadToken, setReloadToken] = useState(0);

  // Loading is reset synchronously in reload() itself (a plain handler,
  // e.g. the "Reload case" stale-decision button and the post-decision
  // refresh) rather than inside the effect body. The parent additionally
  // remounts this component fresh (key={understandingKey}) on every case
  // switch, so the initial mount never needs a reset either.
  const reload = useCallback(() => {
    setDetailState({ status: "loading" });
    setReloadToken((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    entityResolutionApi
      .caseDetail(understandingKey, controller.signal)
      .then((detail) => {
        setDetailState({ status: "ready", detail });
        setSelectedPolicyId((current) => current || detail.policy_id || "");
      })
      .catch((error: unknown) => {
        if (error instanceof Error && error.name === "AbortError") return;
        if (error instanceof EntityResolutionApiError) {
          if (error.problem.code === "AUTH_REQUIRED" || error.status === 401) {
            setDetailState({ status: "unauthorized" });
            return;
          }
          if (error.status === 404) {
            setDetailState({ status: "not-found" });
            return;
          }
          setDetailState({ status: "error", message: error.problem.message });
          return;
        }
        setDetailState({
          status: "error",
          message: "The case could not be loaded.",
        });
      });
    return () => controller.abort();
  }, [understandingKey, reloadToken]);

  useEffect(() => {
    const controller = new AbortController();
    entityResolutionApi
      .policies(controller.signal)
      .then((result) =>
        setPoliciesState({ status: "ready", items: result.items }),
      )
      .catch((error: unknown) => {
        if (error instanceof Error && error.name === "AbortError") return;
        setPoliciesState({ status: "error" });
      });
    return () => controller.abort();
  }, [understandingKey]);

  function handleDecided() {
    onDecided();
    reload();
  }

  return (
    <section className="panel" aria-label="Case detail">
      <div className="action-row" style={{ justifyContent: "space-between" }}>
        <h2 style={{ margin: 0 }}>Case detail</h2>
        <button type="button" className="secondary" onClick={onClose}>
          Close
        </button>
      </div>

      {detailState.status === "loading" && (
        <p role="status">Loading case detail…</p>
      )}

      {detailState.status === "unauthorized" && (
        <div role="alert">
          <p style={{ fontWeight: 700 }}>Sign in required</p>
          <p style={{ color: "var(--muted)" }}>
            Your session expired. Sign in again to view this case.
          </p>
        </div>
      )}

      {detailState.status === "not-found" && (
        <div role="alert">
          <p style={{ fontWeight: 700 }}>Case not found</p>
          <p style={{ color: "var(--muted)" }}>
            This case is no longer available, or does not belong to your tenant.
          </p>
        </div>
      )}

      {detailState.status === "error" && (
        <div className="error-summary" role="alert">
          <p>{detailState.message}</p>
          <button type="button" className="secondary" onClick={reload}>
            Retry
          </button>
        </div>
      )}

      {detailState.status === "ready" && (
        <>
          <dl className="status-grid">
            <div>
              <dt>Outcome</dt>
              <dd>{detailState.detail.outcome}</dd>
            </div>
            <div>
              <dt>Confidence</dt>
              <dd>{detailState.detail.business_confidence}</dd>
            </div>
            <div>
              <dt>Policy</dt>
              <dd>
                {detailState.detail.policy_name ?? "—"} (
                {detailState.detail.policy_version})
              </dd>
            </div>
          </dl>

          <p style={{ marginTop: "1rem" }}>
            <strong>Canonical candidate:</strong>{" "}
            {detailState.detail.candidate_enterprise_entity_name ??
              "No candidate attached"}
          </p>
          <p>{detailState.detail.narrative_explanation}</p>

          {detailState.detail.structured_reasons.length > 0 && (
            <div className="conditions">
              <h3>Reasons</h3>
              <ul>
                {detailState.detail.structured_reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </div>
          )}

          <h3 style={{ marginTop: "1.5rem" }}>Source representations</h3>
          {detailState.detail.source_representations.length === 0 ? (
            <p style={{ color: "var(--muted)" }}>
              No source representations are recorded for this case.
            </p>
          ) : (
            <div className="table-wrap">
              <table>
                <caption className="sr-only">Source representations</caption>
                <thead>
                  <tr>
                    <th>Source object</th>
                    <th>Source system</th>
                  </tr>
                </thead>
                <tbody>
                  {detailState.detail.source_representations.map((rep) => (
                    <tr key={rep.source_object_id}>
                      <td>{rep.source_object_name}</td>
                      <td>{rep.source_system_name}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div style={{ marginTop: "1rem" }}>
            <EvidenceList profile={detailState.detail.evidence_profile} />
          </div>

          {detailState.detail.previous_decision && (
            <div className="conditions" style={{ marginTop: "1rem" }}>
              <h3>Prior understanding</h3>
              <p style={{ color: "var(--muted)" }}>
                {detailState.detail.prior_decision_count} prior record(s). Most
                recent: {detailState.detail.previous_decision.outcome} (
                {detailState.detail.previous_decision.business_confidence}) by{" "}
                {detailState.detail.previous_decision.actor_id ??
                  "the automated engine"}{" "}
                on{" "}
                {formatDate(detailState.detail.previous_decision.produced_at)}
                {detailState.detail.previous_decision.decision_rationale && (
                  <>
                    {" "}
                    — “{detailState.detail.previous_decision.decision_rationale}
                    ”
                  </>
                )}
              </p>
            </div>
          )}

          <div style={{ marginTop: "1rem" }}>
            {policiesState.status === "ready" && (
              <PolicyPreviewPanel
                understandingKey={understandingKey}
                policies={policiesState.items}
                selectedPolicyId={selectedPolicyId}
                onSelectedPolicyIdChange={setSelectedPolicyId}
              />
            )}
            {policiesState.status === "error" && (
              <div className="error-summary" role="alert">
                Available policies could not be loaded, so decisions cannot be
                recorded right now.
              </div>
            )}
          </div>

          <section className="panel" aria-label="Steward decision">
            <h3>Record a decision</h3>
            <p style={{ color: "var(--muted)" }}>
              Every decision requires a rationale and is recorded against the
              policy selected above.
            </p>
            <div className="action-row" style={{ flexWrap: "wrap" }}>
              {ACTIONS.map((action) => (
                <DecisionDialog
                  key={action}
                  action={action}
                  understandingKey={understandingKey}
                  policyId={selectedPolicyId || null}
                  basedOnRecordId={detailState.detail.record_id}
                  onDecided={handleDecided}
                  onStale={reload}
                />
              ))}
            </div>
          </section>
        </>
      )}
    </section>
  );
}
