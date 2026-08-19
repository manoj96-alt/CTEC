import { render } from "@testing-library/react";
import { axe } from "vitest-axe";
import { AlternativesPanel } from "@/app/supply-chain-impact/_components/alternatives-panel";
import { BusinessImpactPanel } from "@/app/supply-chain-impact/_components/business-impact-panel";
import { EvidencePanel } from "@/app/supply-chain-impact/_components/evidence-panel";
import { HumanAuthorityBanner } from "@/app/supply-chain-impact/_components/human-authority-banner";
import { RecommendationPanel } from "@/app/supply-chain-impact/_components/recommendation-panel";
import { RiskSignalPanel } from "@/app/supply-chain-impact/_components/risk-signal-panel";
import type {
  CandidateOutcome,
  ImpactSummary,
  MaterialEvaluationResult,
} from "@/lib/supply-chain-impact/contracts";

const evidence = [
  {
    source_system_name: "Gate F Demo Risk Platform",
    predicate: "severity",
    value: "Severe",
    asserted_on: "2026-01-01T00:00:00Z",
  },
];

const candidate: CandidateOutcome = {
  alternate_supplier_entity_id: "11111111-1111-1111-1111-111111111111",
  outcome: "Recommended",
  reason: "All four governed conditions are satisfied",
  decision_record_identifier: "22222222-2222-2222-2222-222222222222",
  structured_reasons: ["Recommended: all four governed conditions are satisfied"],
  narrative: "Gate F governed four-condition mitigation policy.",
  confidence: "High",
  evidence,
};

const material: MaterialEvaluationResult = {
  material_entity_id: "33333333-3333-3333-3333-333333333333",
  high_severity_disruption: true,
  single_source_exposure: true,
  revenue_materiality: true,
  candidates: [candidate],
};

const impact: ImpactSummary = {
  supplier_entity_id: "44444444-4444-4444-4444-444444444444",
  supplier_name: "Demo Supplier",
  materials: [{ material_entity_id: material.material_entity_id, material_name: "Demo Material" }],
  products: [{ entity_id: "5", entity_name: "Demo Product" }],
  facilities: [{ entity_id: "6", entity_name: "Demo Facility" }],
  revenue_exposures: [{ entity_id: "7", entity_name: "Demo Revenue Exposure" }],
};

test("governed supplier-risk panels have no automated accessibility violations", async () => {
  const { container } = render(
    <main>
      <RiskSignalPanel supplierName={impact.supplier_name} material={material} evidence={evidence} />
      <BusinessImpactPanel
        impact={impact}
        singleSourceExposure={material.single_source_exposure}
        revenueMateriality={material.revenue_materiality}
        evidence={evidence}
      />
      <EvidencePanel evidence={evidence} />
      <AlternativesPanel candidates={material.candidates} />
      <RecommendationPanel candidate={candidate} policyReference="CDD-015-Gate-F-Mitigation-Policy" policyVersion="2.0" />
      <HumanAuthorityBanner governanceStanding="HUMAN_APPROVAL_REQUIRED" />
    </main>,
  );
  const results = await axe(container, {
    rules: { "color-contrast": { enabled: false } },
  });
  expect(results.violations).toHaveLength(0);
});
