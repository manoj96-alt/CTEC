import { expect, test } from "vitest";
import {
  evaluateDecision,
  MATERIALITY_THRESHOLD_USD,
} from "@/lib/demo/decision-rules";
import { buildTestScenarioFacts } from "./helpers/demo-fixture";

test("all four conditions pass for the primary scenario and produce the expected recommendation", () => {
  const evaluation = evaluateDecision(buildTestScenarioFacts());

  expect(evaluation.conditions.every((c) => c.passed)).toBe(true);
  expect(evaluation.recommended).toBe(true);
  expect(evaluation.recommendation).not.toBeNull();
  expect(evaluation.recommendation?.proposedAllocationPct).toBe(40);
  expect(evaluation.recommendation?.remainingExposurePct).toBe(60);
  expect(evaluation.recommendation?.activationLeadTimeDays).toBe(21);
  expect(evaluation.recommendation?.unitCostIncreasePct).toBe(7);
});

test("Nova capacity at 60% supports the proposed 40% allocation", () => {
  const evaluation = evaluateDecision(
    buildTestScenarioFacts({ candidateCapacityPct: 60 }),
  );
  expect(evaluation.recommendation?.proposedAllocationPct).toBe(40);
});

test("Nova capacity below 40% reduces the recommended allocation below the 40% cap", () => {
  const evaluation = evaluateDecision(
    buildTestScenarioFacts({ candidateCapacityPct: 25 }),
  );
  expect(evaluation.recommended).toBe(true);
  expect(evaluation.recommendation?.proposedAllocationPct).toBe(25);
  expect(evaluation.recommendation?.remainingExposurePct).toBe(75);
});

test("an unqualified alternate supplier is not recommended for activation", () => {
  const evaluation = evaluateDecision(
    buildTestScenarioFacts({ candidateStatus: "UnderReview" }),
  );
  const capacityCondition = evaluation.conditions.find(
    (c) => c.key === "alternateHasCapacity",
  );
  expect(capacityCondition?.passed).toBe(false);
  expect(evaluation.recommended).toBe(false);
  expect(evaluation.recommendation).toBeNull();
});

test("no recommendation is produced when the material is not single-sourced", () => {
  const evaluation = evaluateDecision(
    buildTestScenarioFacts({ sourcingPct: 60 }),
  );

  const sourcingCondition = evaluation.conditions.find(
    (c) => c.key === "singleSourced",
  );
  expect(sourcingCondition?.passed).toBe(false);
  expect(evaluation.recommended).toBe(false);
  expect(evaluation.recommendation).toBeNull();
});

test("no recommendation is produced when the candidate has no available capacity", () => {
  const evaluation = evaluateDecision(
    buildTestScenarioFacts({ candidateCapacityPct: 0 }),
  );

  const capacityCondition = evaluation.conditions.find(
    (c) => c.key === "alternateHasCapacity",
  );
  expect(capacityCondition?.passed).toBe(false);
  expect(evaluation.recommended).toBe(false);
});

test("lower revenue exposure suppresses the materiality trigger and the recommendation", () => {
  const evaluation = evaluateDecision(
    buildTestScenarioFacts({ revenueUsd: MATERIALITY_THRESHOLD_USD - 1 }),
  );

  const revenueCondition = evaluation.conditions.find(
    (c) => c.key === "revenueExceedsThreshold",
  );
  expect(revenueCondition?.passed).toBe(false);
  expect(evaluation.recommended).toBe(false);
  expect(evaluation.recommendation).toBeNull();
});
