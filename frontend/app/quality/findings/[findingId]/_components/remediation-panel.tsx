import { useState } from "react";
import { StatusIndicator } from "@/components/design-system/status-indicator";
import type {
  RemediationCandidateItemView,
  RemediationResponse,
} from "@/lib/oqi/contracts";
import { OqiApiError, oqiApi } from "@/lib/oqi/api-client";
import { DecideAuthorizationDialog } from "./decide-authorization-dialog";
import { RemediationStepper } from "./remediation-stepper";
import { ReportExecutionDialog } from "./report-execution-dialog";

// CDD-045 §20/§48-49/§29 UI Truth Table -- the highest-stakes panel in the
// whole product. Recommendation, human authorization, and external
// remediation are always three visually and structurally distinct facts.
// "External remediation reported" never becomes "Resolved" here -- only a
// Finding transitioning to RESOLVED via the real deterministic evaluator
// (rendered on the parent Finding-detail shell) may ever say that.
//
// CDD-085 G-R3 §6/§7/§17/§18 + G-R4/G-R5: the plural remediation contract.
// Every candidate the last Prepare produced is rendered, each with its own
// governed action -- a genuine CROSS_SOURCE_VALUE_CONFLICT case (Golden's
// real US/MX candidates) is never collapsed to one arbitrary candidate.
// Once one candidate is APPROVED, its siblings show SUPERSEDED with honest
// explanatory copy -- never implying the superseded candidate was false.
// UI disablement of a superseded candidate's own action is cosmetic only;
// the backend transaction and the database partial unique index remain the
// actual enforcement boundary.
//
// Execution-gate invariant (G-R4 §13/§39, preserved from the pre-plural
// design): report-execution is offered only for the APPROVED candidate AND
// only while the case-level external_execution has not already been
// recorded -- once reported, no candidate (including a still-APPROVED one)
// may expose a second Report Execution action. This is a per-case gate,
// not a per-candidate one; the plural rewrite must not accidentally make
// execution repeatable merely because an APPROVED candidate remains
// displayed.
export function RemediationPanel({
  remediation,
  findingId,
  onMutated,
}: {
  remediation: RemediationResponse;
  findingId: string;
  onMutated: () => void;
}) {
  const [preparing, setPreparing] = useState(false);
  const [prepareError, setPrepareError] = useState<string | null>(null);

  const hasNothing =
    remediation.candidates.length === 0 &&
    !remediation.recommendation &&
    !remediation.external_execution;

  async function handlePrepare() {
    if (preparing) return;
    setPreparing(true);
    setPrepareError(null);
    try {
      await oqiApi.prepareRemediation(findingId);
      onMutated();
    } catch (caught) {
      setPrepareError(
        caught instanceof OqiApiError
          ? `Remediation could not be prepared (${caught.code}).`
          : "Remediation could not be prepared.",
      );
    } finally {
      setPreparing(false);
    }
  }

  if (hasNothing) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <h3>Remediation</h3>
        <RemediationStepper remediation={remediation} />
        <p>No remediation activity recorded for this Finding.</p>
        <div>
          <button
            type="button"
            disabled={preparing}
            onClick={() => void handlePrepare()}
          >
            {preparing ? "Preparing…" : "Prepare remediation"}
          </button>
        </div>
        {prepareError && (
          <div className="error-summary" role="alert">
            {prepareError}
          </div>
        )}
      </div>
    );
  }

  const externalExecutionReported = remediation.external_execution !== null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <h3>Remediation</h3>

      <RemediationStepper remediation={remediation} />

      {remediation.candidates.map((item) => (
        <RemediationCandidateCard
          key={item.candidate_id}
          item={item}
          externalExecutionReported={externalExecutionReported}
          onMutated={onMutated}
        />
      ))}

      <div className="panel obs-gate-card obs-gate-card--recommendation">
        <span className="eyebrow">Agent Recommendation</span>
        {remediation.recommendation ? (
          <>
            <h4 style={{ marginTop: "0.25rem" }}>
              {remediation.recommendation.recommendation_type}
            </h4>
            <p>{remediation.recommendation.rationale}</p>
          </>
        ) : (
          <p>No agent recommendation exists for this Finding.</p>
        )}
      </div>

      <div className="panel obs-gate-card obs-gate-card--remediation">
        <span className="eyebrow">External Remediation</span>
        {remediation.external_execution ? (
          <>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              <StatusIndicator status="attention" />
              <p style={{ fontWeight: 700, margin: 0 }}>
                External remediation reported — awaiting fresh evidence
              </p>
            </div>
            <p>
              Reported at{" "}
              {new Date(
                remediation.external_execution.reported_at,
              ).toLocaleString()}
            </p>
            <p style={{ color: "var(--muted)" }}>
              This does not by itself resolve the underlying quality condition.
              Only fresh source evidence and deterministic re-evaluation can do
              that.
            </p>
          </>
        ) : (
          <p>No external remediation has been reported for this Finding.</p>
        )}
      </div>
    </div>
  );
}

// CDD-085 G-R3 §17/§18: one candidate's own card -- proposed value, basis,
// and its own authorization state/action, never a case-wide "the" state.
function RemediationCandidateCard({
  item,
  externalExecutionReported,
  onMutated,
}: {
  item: RemediationCandidateItemView;
  externalExecutionReported: boolean;
  onMutated: () => void;
}) {
  const authorization = item.authorization;
  const canDecide =
    authorization !== null && authorization.status === "PENDING";
  // Execution-gate invariant: APPROVED alone is insufficient -- the
  // case-level externalExecutionReported gate (threaded from the parent,
  // never re-derived per candidate) must also hold, preserving the
  // pre-plural design's exact "at most one execution report per case"
  // behavior. SUPERSEDED/REJECTED/PENDING are never executable regardless.
  const canReportExecution =
    authorization !== null &&
    authorization.status === "APPROVED" &&
    !externalExecutionReported;
  const instruction = `Update to "${item.proposed_value}"`;

  return (
    <div className="panel obs-gate-card">
      <span className="eyebrow">Deterministic candidate</span>
      <h4 style={{ marginTop: "0.25rem" }}>{item.proposed_value}</h4>
      <p style={{ fontWeight: 700 }}>Candidate — not established truth</p>

      {authorization ? (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            marginTop: "0.5rem",
          }}
        >
          <StatusIndicator
            status={
              authorization.status === "REJECTED"
                ? "conflict"
                : authorization.status === "SUPERSEDED"
                  ? "attention"
                  : authorization.decided_on
                    ? "verified"
                    : "pending"
            }
          />
          <h5 style={{ margin: 0 }}>
            {authorization.status === "SUPERSEDED"
              ? "Superseded — an alternative candidate was approved"
              : authorization.decided_on
                ? `${authorization.status === "APPROVED" ? "Authorized" : "Rejected"} by ${authorization.decided_by} at ${new Date(authorization.decided_on).toLocaleString()}`
                : "Authorization pending decision"}
          </h5>
        </div>
      ) : (
        <p>No human authorization exists for this candidate.</p>
      )}

      {authorization?.is_stale ? (
        <p role="alert" style={{ fontWeight: 700 }}>
          Stale — this authorization no longer matches the current Finding state
          and cannot be used.
        </p>
      ) : null}

      {canDecide && authorization ? (
        <div style={{ marginTop: "0.5rem" }}>
          <DecideAuthorizationDialog
            authorizationId={authorization.authorization_id}
            instruction={instruction}
            onDecided={onMutated}
          />
        </div>
      ) : null}

      {canReportExecution && authorization ? (
        <div style={{ marginTop: "0.5rem" }}>
          <ReportExecutionDialog
            authorizationId={authorization.authorization_id}
            onReported={onMutated}
          />
        </div>
      ) : null}
    </div>
  );
}
