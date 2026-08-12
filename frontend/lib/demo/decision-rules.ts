// Pure transform of already-resolved scenario facts into a decision
// evaluation. Consumes ScenarioFacts (scenario-facts.ts) — the same
// resolved records the ontology model renders — rather than independently
// re-querying the raw dataset, so decision logic can never drift out of
// sync with what the ontology stage showed.

import type { ScenarioFacts } from "./scenario-facts";
import { PRIMARY_MATERIAL_ID } from "./scenario-facts";
import type { SourceRef } from "./types";

export const MATERIALITY_THRESHOLD_USD = 10_000_000;

export interface DecisionFactor {
  key: string;
  label: string;
  detail: string;
  sourceRefs: SourceRef[];
}

export interface RuleCondition {
  key: string;
  label: string;
  detail: string;
  passed: boolean;
  sourceRefs: SourceRef[];
}

export interface Recommendation {
  summary: string;
  proposedAllocationPct: number;
  remainingExposurePct: number;
  activationLeadTimeDays: number;
  unitCostIncreasePct: number;
}

export interface DecisionEvaluation {
  factors: DecisionFactor[];
  conditions: RuleCondition[];
  recommended: boolean;
  recommendation: Recommendation | null;
  assumptions: string[];
  missingInformation: string[];
}

export function evaluateDecision(facts: ScenarioFacts): DecisionEvaluation {
  const { supplier, candidate, agreement, riskEvent, revenue } = facts;

  const highSeverityDisruption = riskEvent.severity === "Severe";
  const singleSourced = agreement.sourcingPct === 100;
  const revenueExceedsThreshold =
    revenue.annualRevenueUsd > MATERIALITY_THRESHOLD_USD;
  const alternateHasCapacity =
    candidate.qualificationStatus === "Qualified" &&
    candidate.availableCapacityPct > 0;

  const conditions: RuleCondition[] = [
    {
      key: "highSeverityDisruption",
      label: "Supplier disruption severity is high",
      detail: `${riskEvent.severity} — ${riskEvent.description}`,
      passed: highSeverityDisruption,
      sourceRefs: [riskEvent.sourceRef],
    },
    {
      key: "singleSourced",
      label: "Affected material is single-sourced",
      detail: `${agreement.sourcingPct}% of ${PRIMARY_MATERIAL_ID} sourced from ${supplier.supplierName}`,
      passed: singleSourced,
      sourceRefs: [agreement.sourceRef],
    },
    {
      key: "revenueExceedsThreshold",
      label: "Revenue exposure exceeds materiality threshold",
      detail: `$${(revenue.annualRevenueUsd / 1_000_000).toFixed(0)}M exposure vs. $${(MATERIALITY_THRESHOLD_USD / 1_000_000).toFixed(0)}M threshold`,
      passed: revenueExceedsThreshold,
      sourceRefs: [revenue.sourceRef],
    },
    {
      key: "alternateHasCapacity",
      label: "A qualified alternate supplier has available capacity",
      detail: `${candidate.supplierName} — ${candidate.qualificationStatus}, ${candidate.availableCapacityPct}% capacity available`,
      passed: alternateHasCapacity,
      sourceRefs: [candidate.sourceRef],
    },
  ];

  const factors: DecisionFactor[] = [
    {
      key: "disruptionSeverity",
      label: "Disruption severity",
      detail: `${riskEvent.severity} regional logistics disruption affects ${supplier.supplierName}.`,
      sourceRefs: [riskEvent.sourceRef],
    },
    {
      key: "sourcingConcentration",
      label: "Sourcing concentration",
      detail: `${supplier.supplierName} currently supplies ${agreement.sourcingPct}% of ${PRIMARY_MATERIAL_ID} demand.`,
      sourceRefs: [agreement.sourceRef],
    },
    {
      key: "businessImpact",
      label: "Business impact",
      detail: `This material is required by the affected product, creating $${(revenue.annualRevenueUsd / 1_000_000).toFixed(0)}M in annual revenue exposure.`,
      sourceRefs: [revenue.sourceRef],
    },
    {
      key: "alternateReadiness",
      label: "Alternate supplier readiness",
      detail: `${candidate.supplierName} is ${candidate.qualificationStatus.toLowerCase()} and can initially absorb ${candidate.availableCapacityPct}% of demand.`,
      sourceRefs: [candidate.sourceRef],
    },
    {
      key: "activationTime",
      label: "Activation time",
      detail: `${candidate.supplierName} requires approximately ${candidate.activationLeadTimeDays} days to begin supply.`,
      sourceRefs: [candidate.sourceRef],
    },
    {
      key: "costImpact",
      label: "Cost impact",
      detail: `${candidate.supplierName}'s unit cost is approximately ${candidate.unitCostIndexPct - 100}% higher than the current supplier.`,
      sourceRefs: [candidate.sourceRef, supplier.sourceRef],
    },
    {
      key: "riskReduction",
      label: "Risk reduction",
      detail: `Moving a share of demand to ${candidate.supplierName} would reduce complete dependency on ${supplier.supplierName} while remaining within available capacity.`,
      sourceRefs: [candidate.sourceRef, agreement.sourceRef],
    },
  ];

  const recommended = conditions.every((condition) => condition.passed);
  const proposedAllocationPct = recommended
    ? Math.min(candidate.availableCapacityPct, 40)
    : 0;

  const recommendation: Recommendation | null = recommended
    ? {
        summary: `Activate ${candidate.supplierName} as a secondary supplier for ${proposedAllocationPct}% of ${PRIMARY_MATERIAL_ID} demand and begin accelerated capacity qualification.`,
        proposedAllocationPct,
        remainingExposurePct: 100 - proposedAllocationPct,
        activationLeadTimeDays: candidate.activationLeadTimeDays,
        unitCostIncreasePct: candidate.unitCostIndexPct - 100,
      }
    : null;

  return {
    factors,
    conditions,
    recommended,
    recommendation,
    assumptions: [
      `${candidate.supplierName}'s stated activation lead time and unit cost are taken as given from its supplier record and are not independently re-verified in this demo.`,
      "The materiality threshold used here is a demo default, not a customer-approved policy value.",
    ],
    missingInformation: [
      "No estimate of how long the regional disruption is expected to last was available in the imported dataset.",
      "No contractual penalty or exit terms for reducing Apex Components' allocation were available in the imported dataset.",
    ],
  };
}
