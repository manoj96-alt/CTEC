"use client";

import { useState } from "react";
import type { DecisionEvaluation } from "@/lib/demo/decision-rules";

export interface RecommendationStageProps {
  evaluation: DecisionEvaluation;
  onDecision: (decision: "Approved" | "Rejected", comment: string) => void;
  hasDecided: boolean;
}

export function RecommendationStage({
  evaluation,
  onDecision,
  hasDecided,
}: RecommendationStageProps) {
  const [comment, setComment] = useState("");
  const { recommendation } = evaluation;

  return (
    <section>
      <p className="eyebrow">Stage 5 of 5</p>
      <h2 style={{ marginTop: "0.25rem" }}>Recommendation</h2>

      {!recommendation && (
        <p style={{ color: "var(--muted)" }}>
          No recommendation was generated — not all decision conditions were
          met.
        </p>
      )}

      {recommendation && (
        <>
          <div
            className="panel"
            style={{
              padding: "1.25rem",
              marginTop: "1rem",
              borderColor: "var(--accent)",
            }}
          >
            <p
              style={{
                fontWeight: 700,
                fontSize: "1.05rem",
                marginBottom: "1rem",
              }}
            >
              {recommendation.summary}
            </p>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(10rem, 1fr))",
                gap: "0.75rem",
                fontSize: "0.85rem",
              }}
            >
              <div>
                <p style={{ margin: 0, color: "var(--muted)" }}>
                  Proposed allocation
                </p>
                <p style={{ margin: 0, fontWeight: 700 }}>
                  {recommendation.proposedAllocationPct}%
                </p>
              </div>
              <div>
                <p style={{ margin: 0, color: "var(--muted)" }}>
                  Remaining Apex exposure
                </p>
                <p style={{ margin: 0, fontWeight: 700 }}>
                  {recommendation.remainingExposurePct}%
                </p>
              </div>
              <div>
                <p style={{ margin: 0, color: "var(--muted)" }}>
                  Activation period
                </p>
                <p style={{ margin: 0, fontWeight: 700 }}>
                  {recommendation.activationLeadTimeDays} days
                </p>
              </div>
              <div>
                <p style={{ margin: 0, color: "var(--muted)" }}>
                  Unit cost increase
                </p>
                <p style={{ margin: 0, fontWeight: 700 }}>
                  {recommendation.unitCostIncreasePct}%
                </p>
              </div>
            </div>
          </div>

          <div className="panel" style={{ padding: "1rem", marginTop: "1rem" }}>
            <p style={{ fontWeight: 700, marginBottom: "0.5rem" }}>
              Evidence supporting this recommendation
            </p>
            <ul
              style={{
                margin: 0,
                paddingLeft: "1.2rem",
                fontSize: "0.85rem",
                color: "var(--muted)",
              }}
            >
              {evaluation.conditions.map((condition) => (
                <li key={condition.key}>{condition.detail}</li>
              ))}
            </ul>
          </div>

          <div className="panel" style={{ padding: "1rem", marginTop: "1rem" }}>
            <p style={{ fontWeight: 700, marginBottom: "0.5rem" }}>
              Assumptions and limitations
            </p>
            <ul
              style={{
                margin: 0,
                paddingLeft: "1.2rem",
                fontSize: "0.85rem",
                color: "var(--muted)",
              }}
            >
              {[
                ...evaluation.assumptions,
                ...evaluation.missingInformation,
              ].map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <label
            style={{
              display: "block",
              marginTop: "1rem",
              fontSize: "0.85rem",
              color: "var(--muted)",
            }}
          >
            Decision comment (optional)
            <textarea
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              rows={2}
              style={{
                display: "block",
                width: "100%",
                marginTop: "0.35rem",
                padding: "0.5rem",
                borderRadius: "0.5rem",
                border: "1px solid var(--line)",
                font: "inherit",
              }}
            />
          </label>

          <div style={{ display: "flex", gap: "0.75rem", marginTop: "1rem" }}>
            <button
              type="button"
              disabled={hasDecided}
              onClick={() => onDecision("Approved", comment)}
            >
              Approve Recommendation
            </button>
            <button
              type="button"
              className="secondary"
              disabled={hasDecided}
              onClick={() => onDecision("Rejected", comment)}
            >
              Reject Recommendation
            </button>
          </div>
          {hasDecided && (
            <p
              style={{
                marginTop: "0.75rem",
                fontSize: "0.85rem",
                color: "var(--muted)",
              }}
            >
              Decision recorded below. Use Reset Demo to run through the
              scenario again.
            </p>
          )}
        </>
      )}
    </section>
  );
}
