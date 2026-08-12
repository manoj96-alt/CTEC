// Pure transform of already-resolved scenario facts into a node/edge graph.
// This module does NOT query the raw dataset itself — resolveScenarioFacts()
// (scenario-facts.ts) is the single place that happens, so there is exactly
// one source of truth for "which records make up this scenario."

import type { SourceRef } from "./types";
import type { ScenarioFacts } from "./scenario-facts";

export type OntologyNodeKind =
  | "supplier"
  | "candidateSupplier"
  | "material"
  | "product"
  | "facility"
  | "revenue"
  | "region"
  | "riskEvent"
  | "agreement";

export interface OntologyNode {
  id: string;
  kind: OntologyNodeKind;
  label: string;
  detailLines: string[];
  sourceRefs: SourceRef[];
  onRiskPath: boolean;
}

export interface OntologyEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  onRiskPath: boolean;
}

export interface ImpactSummary {
  criticalSuppliersAffected: number;
  criticalMaterialsAffected: number;
  productsAffected: number;
  facilitiesExposed: number;
  annualRevenueExposureUsd: number;
  secondarySourceActive: boolean;
}

export interface OntologyModel {
  nodes: OntologyNode[];
  edges: OntologyEdge[];
  impactSummary: ImpactSummary;
}

export function buildOntologyModel(facts: ScenarioFacts): OntologyModel {
  const {
    supplier,
    candidate,
    material,
    product,
    facility,
    agreement,
    riskEvent,
    revenue,
  } = facts;

  const revenueLabel = `$${(revenue.annualRevenueUsd / 1_000_000).toFixed(0)}M Annual Revenue`;

  const nodes: OntologyNode[] = [
    {
      id: `supplier:${supplier.supplierId}`,
      kind: "supplier",
      label: supplier.supplierName,
      detailLines: [
        `Status: ${supplier.qualificationStatus}`,
        `Region: ${supplier.regionName}`,
      ],
      sourceRefs: [supplier.sourceRef],
      onRiskPath: true,
    },
    {
      id: `material:${material.materialId}`,
      kind: "material",
      label: material.materialName,
      detailLines: [`Unit cost: $${material.unitCostUsd.toFixed(2)}`],
      sourceRefs: [material.sourceRef],
      onRiskPath: true,
    },
    {
      id: `product:${product.productId}`,
      kind: "product",
      label: product.productName,
      detailLines: [],
      sourceRefs: [product.sourceRef],
      onRiskPath: true,
    },
    {
      id: `facility:${facility.facilityId}`,
      kind: "facility",
      label: facility.facilityName,
      detailLines: [`Region: ${facility.regionName}`],
      sourceRefs: [facility.sourceRef],
      onRiskPath: true,
    },
    {
      id: "revenue:primary",
      kind: "revenue",
      label: revenueLabel,
      detailLines: ["Annual revenue tied to this product."],
      sourceRefs: [revenue.sourceRef],
      onRiskPath: true,
    },
    {
      id: `region:${supplier.regionId}`,
      kind: "region",
      label: supplier.regionName,
      detailLines: [],
      sourceRefs: [supplier.sourceRef],
      onRiskPath: true,
    },
    {
      id: `riskEvent:${riskEvent.riskEventId}`,
      kind: "riskEvent",
      label:
        riskEvent.severity === "Severe"
          ? "Severe Regional Logistics Disruption"
          : riskEvent.description,
      detailLines: [riskEvent.description],
      sourceRefs: [riskEvent.sourceRef],
      onRiskPath: true,
    },
    {
      id: `agreement:${agreement.agreementId}`,
      kind: "agreement",
      label: `Supply Agreement ${agreement.agreementId}`,
      detailLines: [
        `${agreement.sourcingPct}% sourced from ${supplier.supplierName}`,
        agreement.terms,
      ],
      sourceRefs: [agreement.sourceRef],
      onRiskPath: true,
    },
    {
      id: `candidate:${candidate.supplierId}`,
      kind: "candidateSupplier",
      label: candidate.supplierName,
      detailLines: [
        `Status: ${candidate.qualificationStatus}`,
        `Available capacity: ${candidate.availableCapacityPct}%`,
        `Activation lead time: ${candidate.activationLeadTimeDays} days`,
      ],
      sourceRefs: [candidate.sourceRef],
      onRiskPath: false,
    },
  ];

  const edges: OntologyEdge[] = [
    {
      id: "e-supplies",
      source: `supplier:${supplier.supplierId}`,
      target: `material:${material.materialId}`,
      label: "supplies",
      onRiskPath: true,
    },
    {
      id: "e-used-in",
      source: `material:${material.materialId}`,
      target: `product:${product.productId}`,
      label: "used in",
      onRiskPath: true,
    },
    {
      id: "e-assembled-at",
      source: `product:${product.productId}`,
      target: `facility:${facility.facilityId}`,
      label: "assembled at",
      onRiskPath: true,
    },
    {
      id: "e-generates-revenue",
      source: `facility:${facility.facilityId}`,
      target: "revenue:primary",
      label: "generates revenue",
      onRiskPath: true,
    },
    {
      id: "e-located-in",
      source: `supplier:${supplier.supplierId}`,
      target: `region:${supplier.regionId}`,
      label: "located in",
      onRiskPath: true,
    },
    {
      id: "e-affected-by",
      source: `region:${supplier.regionId}`,
      target: `riskEvent:${riskEvent.riskEventId}`,
      label: "affected by",
      onRiskPath: true,
    },
    {
      id: "e-covered-by",
      source: `material:${material.materialId}`,
      target: `agreement:${agreement.agreementId}`,
      label: "covered by",
      onRiskPath: true,
    },
    {
      id: "e-alternate-for",
      source: `candidate:${candidate.supplierId}`,
      target: `material:${material.materialId}`,
      label: "candidate alternate for",
      onRiskPath: false,
    },
  ];

  const impactSummary: ImpactSummary = {
    criticalSuppliersAffected: 1,
    criticalMaterialsAffected: 1,
    productsAffected: 1,
    facilitiesExposed: 1,
    annualRevenueExposureUsd: revenue.annualRevenueUsd,
    secondarySourceActive: agreement.sourcingPct < 100,
  };

  return { nodes, edges, impactSummary };
}
