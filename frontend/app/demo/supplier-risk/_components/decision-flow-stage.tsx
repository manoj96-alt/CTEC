"use client";

import { useState } from "react";
import type { DecisionEvaluation } from "@/lib/demo/decision-rules";

export interface DecisionFlowStageProps {
  evaluation: DecisionEvaluation;
  onContinue: () => void;
}

export function DecisionFlowStage({
  evaluation,
  onContinue,
}: DecisionFlowStageProps) {
  const [showWhy, setShowWhy] = useState(false);

  return (
    <section>
      <p className="eyebrow">Stage 4 of 5</p>
      <h2 style={{ marginTop: "0.25rem" }}>Review Decision Flow</h2>
      <p style={{ color: "var(--muted)", maxWidth: "42rem" }}>
        The recommendation on the next screen is not made by an opaque model. It
        combines the ontology relationships you just explored, the imported
        source evidence, and the explicit business rule below.
      </p>

      <div className="panel" style={{ padding: "1rem", marginTop: "1rem" }}>
        <p style={{ fontWeight: 700, marginBottom: "0.75rem" }}>
          Factors considered
        </p>
        <ul style={{ margin: 0, paddingLeft: "1.2rem", fontSize: "0.88rem" }}>
          {evaluation.factors.map((factor) => (
            <li key={factor.key} style={{ marginBottom: "0.5rem" }}>
              <strong>{factor.label}:</strong> {factor.detail}
            </li>
          ))}
        </ul>
      </div>

      <div className="panel" style={{ padding: "1rem", marginTop: "1rem" }}>
        <p style={{ fontWeight: 700, marginBottom: "0.75rem" }}>
          Decision rule
        </p>
        <p
          style={{
            fontSize: "0.85rem",
            color: "var(--muted)",
            marginBottom: "0.5rem",
          }}
        >
          IF:
        </p>
        <ul style={{ margin: 0, paddingLeft: "1.2rem", fontSize: "0.88rem" }}>
          {evaluation.conditions.map((condition) => (
            <li
              key={condition.key}
              style={{
                marginBottom: "0.4rem",
                color: condition.passed ? "var(--success)" : "var(--danger)",
              }}
            >
              {condition.passed ? "✓" : "✗"} {condition.label}
              <span style={{ color: "var(--muted)" }}>
                {" "}
                — {condition.detail}
              </span>
            </li>
          ))}
        </ul>
        <p
          style={{
            fontSize: "0.85rem",
            color: "var(--muted)",
            margin: "0.75rem 0 0.25rem",
          }}
        >
          THEN:
        </p>
        <p style={{ fontSize: "0.88rem", margin: 0 }}>
          {evaluation.recommended
            ? "Recommend activating the alternate supplier, allocate an initial volume within available capacity, and begin accelerated capacity qualification."
            : "All conditions must be met before a recommendation is generated. Not all conditions are currently met."}
        </p>
      </div>

      <button
        type="button"
        className="secondary"
        onClick={() => setShowWhy((prev) => !prev)}
        style={{ marginTop: "1rem" }}
      >
        {showWhy ? "Hide" : "Why this recommendation?"}
      </button>

      {showWhy && (
        <div
          className="panel"
          style={{ padding: "1rem", marginTop: "0.75rem" }}
          data-testid="why-panel"
        >
          <p style={{ fontWeight: 700, marginBottom: "0.5rem" }}>Assumptions</p>
          <ul
            style={{
              margin: 0,
              paddingLeft: "1.2rem",
              fontSize: "0.85rem",
              color: "var(--muted)",
            }}
          >
            {evaluation.assumptions.map((assumption) => (
              <li key={assumption}>{assumption}</li>
            ))}
          </ul>
          <p style={{ fontWeight: 700, margin: "0.75rem 0 0.5rem" }}>
            Missing information
          </p>
          <ul
            style={{
              margin: 0,
              paddingLeft: "1.2rem",
              fontSize: "0.85rem",
              color: "var(--muted)",
            }}
          >
            {evaluation.missingInformation.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      <button
        type="button"
        onClick={onContinue}
        style={{ marginTop: "1.5rem" }}
      >
        Continue to Recommendation
      </button>
    </section>
  );
}
