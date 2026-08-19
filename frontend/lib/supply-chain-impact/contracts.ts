// Mirrors backend/app/api/supply_chain_impact/schemas.py exactly. No field
// here is ever generated client-side; every value comes from the
// authenticated Gate F API response (CDD-016 §7).

export interface SupplyChainImpactEvaluateRequestBody {
  supplier_entity_id: string;
}

export interface ImpactedEntity {
  entity_id: string;
  entity_name: string;
}

export interface ImpactedMaterial {
  material_entity_id: string;
  material_name: string;
}

export interface ImpactSummary {
  supplier_entity_id: string;
  supplier_name: string;
  materials: ImpactedMaterial[];
  products: ImpactedEntity[];
  facilities: ImpactedEntity[];
  revenue_exposures: ImpactedEntity[];
}

export interface EvidenceItem {
  source_system_name: string;
  predicate: string;
  value: string;
  asserted_on: string;
}

export interface CandidateOutcome {
  alternate_supplier_entity_id: string | null;
  outcome: string | null;
  reason: string | null;
  decision_record_identifier: string | null;
  structured_reasons: string[];
  narrative: string | null;
  confidence: string | null;
  evidence: EvidenceItem[];
}

export interface MaterialEvaluationResult {
  material_entity_id: string;
  high_severity_disruption: boolean | null;
  single_source_exposure: boolean | null;
  revenue_materiality: boolean | null;
  candidates: CandidateOutcome[];
}

export interface SupplyChainImpactEvaluateResponse {
  decision_evaluation_id: string;
  impact: ImpactSummary;
  materials: MaterialEvaluationResult[];
  governance_standing: string | null;
  governance_record_identifier: string | null;
  policy_reference: string;
  policy_version: string;
}

export interface DecisionEvaluationRecord {
  record_identifier: string;
  outcome: string;
  recommendation: string;
  confidence: string;
  structured_reasons: string[];
  narrative: string;
  knowledge_references: string[];
  evidence: EvidenceItem[];
  policy_reference: string;
  policy_version: string;
  effective_from: string;
  produced_timestamp: string;
}

export interface GovernanceEvaluationRecord {
  record_identifier: string;
  governance_outcome: string;
  human_approval_required: boolean;
  policy_reference: string;
  policy_version: string;
  effective_from: string;
  produced_timestamp: string;
}

export interface SupplyChainImpactReadResponse {
  decision_evaluation_id: string;
  created_at: string;
  records: DecisionEvaluationRecord[];
  governance: GovernanceEvaluationRecord | null;
}

// Mirrors the generic (non-stable-error-contract) shape
// `/api/v1/supply-chain-impact` actually returns -- confirmed directly
// against backend/app/main.py's exception handlers, which do not include
// this path prefix in `_STABLE_ERROR_CONTRACT_PATHS`.
export interface ApiProblemDetail {
  code: string;
}

export type ApiProblemBody =
  | { detail: ApiProblemDetail }
  | { detail: Array<{ msg?: string; type?: string }> };
