"use client";

const STEPS = [
  "Import Data",
  "Map Schema",
  "Explore Ontology",
  "Decision Flow",
  "Recommendation",
] as const;

export interface StepIndicatorProps {
  currentStep: number;
  highestCompletedStep: number;
  onStepSelect: (step: number) => void;
}

export function StepIndicator({
  currentStep,
  highestCompletedStep,
  onStepSelect,
}: StepIndicatorProps) {
  return (
    <ol
      aria-label="Demo progress"
      className="flex flex-wrap items-center gap-2 mb-8"
    >
      {STEPS.map((label, index) => {
        const step = index + 1;
        const isCurrent = step === currentStep;
        const isReachable = step <= highestCompletedStep + 1;
        return (
          <li key={label} className="flex items-center gap-2">
            <button
              type="button"
              disabled={!isReachable}
              onClick={() => isReachable && onStepSelect(step)}
              aria-current={isCurrent ? "step" : undefined}
              className="secondary"
              style={{
                padding: "0.4rem 0.85rem",
                fontSize: "0.85rem",
                background: isCurrent ? "var(--accent)" : "white",
                color: isCurrent ? "white" : "var(--ink)",
                borderColor: isCurrent ? "var(--accent)" : "var(--line)",
                cursor: isReachable ? "pointer" : "not-allowed",
                opacity: isReachable ? 1 : 0.45,
              }}
            >
              {step}. {label}
            </button>
            {step < STEPS.length && (
              <span aria-hidden="true" style={{ color: "var(--line)" }}>
                &rarr;
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
