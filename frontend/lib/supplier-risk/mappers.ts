import type { AssessmentDraft, TerminalClassification } from "./contracts";
export function outcomeLabel(value: TerminalClassification | null): string {
  return value ? value.toLowerCase().replaceAll("_", " ") : "In progress";
}
export function submissionBody(
  draft: AssessmentDraft,
  ids: { request: string; correlation: string; session: string },
): object {
  return {
    request_identifier: ids.request,
    correlation_identifier: ids.correlation,
    session_identifier: ids.session,
    supplier_risk: {
      supplier_names: [draft.supplierName],
      source_object_ids: [draft.sourceObjectId],
      enterprise_candidates: [
        [draft.enterpriseEntityId, draft.enterpriseCanonicalName],
      ],
      semantic_terms: [draft.semanticLabel],
      semantic_candidates: [
        [draft.institutionalConceptId, draft.semanticLabel],
      ],
      context_id: draft.contextId,
      material_id: draft.materialId,
      facility_or_region_id: draft.facilityOrRegionId,
      effective_at: new Date(draft.effectiveAt).toISOString(),
      observations: [
        {
          observation_id: draft.observationId,
          source_system_reference: draft.sourceSystemId,
          source_record_reference: draft.sourceRecordReference,
          subject_type: "SUPPLIER",
          subject_id: draft.enterpriseEntityId,
          observation_type: "SUPPLIER_RISK_CONDITION",
          value: draft.observationValue,
          severity: draft.severity,
          observed_at: new Date(draft.observedAt).toISOString(),
          evidence_reference: draft.evidenceReference,
          schema_version: "1.0",
          conflicting: false,
        },
      ],
      supplier_eligibility: [],
      identity_score: draft.identityScore,
      semantic_score: draft.semanticScore,
      assertion_score: draft.assertionScore,
      knowledge_score: draft.knowledgeScore,
      decision_score: draft.decisionScore,
      governance_score: draft.governanceScore,
      identity_policy_version: draft.identityPolicyVersion,
      semantic_policy_version: draft.semanticPolicyVersion,
      assertion_policy_version: draft.assertionPolicyVersion,
      knowledge_policy_version: draft.knowledgePolicyVersion,
      decision_policy_reference: draft.decisionPolicyReference,
      decision_policy_version: draft.decisionPolicyVersion,
      decision_policy_rule: draft.decisionPolicyRule,
      governance_policy_reference: draft.governancePolicyReference,
      governance_policy_version: draft.governancePolicyVersion,
      acceptance_evidence: null,
      governance_conditions: [],
      verified_conditions: [],
      exceptional_policy_condition: false,
    },
  };
}
