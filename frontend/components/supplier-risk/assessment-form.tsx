"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import type { AssessmentDraft } from "@/lib/supplier-risk/contracts";
import { submissionBody } from "@/lib/supplier-risk/mappers";
import { supplierRiskApi } from "@/lib/supplier-risk/api-client";
import { validateAssessment } from "@/lib/supplier-risk/validation";

const blank = (): AssessmentDraft => ({
  supplierName: "",
  sourceObjectId: "",
  enterpriseEntityId: "",
  enterpriseCanonicalName: "",
  institutionalConceptId: "",
  semanticLabel: "",
  contextId: "",
  materialId: "",
  facilityOrRegionId: "",
  sourceSystemId: "",
  sourceRecordReference: "",
  observationId: "",
  observationValue: "",
  evidenceReference: "",
  severity: "MATERIAL",
  observedAt: "",
  effectiveAt: "",
  identityScore: 0,
  semanticScore: 0,
  assertionScore: 0,
  knowledgeScore: 0,
  decisionScore: 0,
  governanceScore: 0,
  identityPolicyVersion: "",
  semanticPolicyVersion: "",
  assertionPolicyVersion: "",
  knowledgePolicyVersion: "",
  decisionPolicyReference: "",
  decisionPolicyVersion: "",
  decisionPolicyRule: "",
  governancePolicyReference: "",
  governancePolicyVersion: "",
});
const textFields: [keyof AssessmentDraft, string][] = [
  ["supplierName", "Supplier name"],
  ["sourceObjectId", "Source object UUID"],
  ["enterpriseEntityId", "Enterprise entity UUID"],
  ["enterpriseCanonicalName", "Enterprise canonical name"],
  ["institutionalConceptId", "Institutional concept UUID"],
  ["semanticLabel", "Semantic label"],
  ["contextId", "Context UUID"],
  ["materialId", "Material UUID"],
  ["facilityOrRegionId", "Facility or region UUID"],
  ["sourceSystemId", "Source system UUID"],
  ["sourceRecordReference", "Source record reference"],
  ["observationId", "Observation UUID"],
  ["observationValue", "Observed risk condition"],
  ["evidenceReference", "Evidence reference"],
  ["identityPolicyVersion", "Identity policy version"],
  ["semanticPolicyVersion", "Semantic policy version"],
  ["assertionPolicyVersion", "Assertion policy version"],
  ["knowledgePolicyVersion", "Knowledge policy version"],
  ["decisionPolicyReference", "Decision policy reference"],
  ["decisionPolicyVersion", "Decision policy version"],
  ["decisionPolicyRule", "Evaluated decision rule"],
  ["governancePolicyReference", "Governance policy reference"],
  ["governancePolicyVersion", "Governance policy version"],
];
const scoreFields: [keyof AssessmentDraft, string][] = [
  ["identityScore", "Identity confidence"],
  ["semanticScore", "Semantic confidence"],
  ["assertionScore", "Assertion confidence"],
  ["knowledgeScore", "Knowledge confidence"],
  ["decisionScore", "Decision confidence"],
  ["governanceScore", "Governance confidence"],
];
export function AssessmentForm() {
  const router = useRouter();
  const [value, setValue] = useState(blank);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState("");
  function update(key: keyof AssessmentDraft, next: string | number) {
    setValue((current) => ({ ...current, [key]: next }));
  }
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const found = validateAssessment(value);
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setProblem("");
    const ids = {
      request: crypto.randomUUID(),
      correlation: crypto.randomUUID(),
      session: crypto.randomUUID(),
    };
    try {
      const response = await supplierRiskApi.submit(
        submissionBody(value, ids),
        ids.request,
      );
      router.push(
        `/supplier-risk/executions/${response.logical_execution_identifier}`,
      );
    } catch (error) {
      setProblem(error instanceof Error ? error.message : "Submission failed");
      setBusy(false);
    }
  }
  return (
    <form className="assessment-form" onSubmit={submit} noValidate>
      <div className="page-heading">
        <div>
          <span className="eyebrow">New assessment</span>
          <h1>Assess supplier risk</h1>
          <p>
            Enter governed source observations and policy references. CTEC
            determines the outcome.
          </p>
        </div>
      </div>
      {Object.keys(errors).length > 0 && (
        <div className="error-summary" role="alert" tabIndex={-1}>
          <strong>Correct the highlighted fields.</strong>
        </div>
      )}
      {problem && (
        <div className="error-summary" role="alert">
          {problem}
        </div>
      )}
      <fieldset>
        <legend>Supplier and context</legend>
        <div className="form-grid">
          {textFields.slice(0, 13).map(([key, label]) => (
            <label key={key}>
              {label}
              <input
                value={String(value[key])}
                onChange={(e) => update(key, e.target.value)}
                aria-invalid={!!errors[key]}
                required
              />
              {errors[key] && <small>{errors[key]}</small>}
            </label>
          ))}
          <label>
            Risk severity
            <select
              value={value.severity}
              onChange={(e) => update("severity", e.target.value)}
            >
              <option>LOW</option>
              <option>MATERIAL</option>
              <option>HIGH</option>
              <option>CRITICAL</option>
            </select>
          </label>
          <label>
            Observed at
            <input
              type="datetime-local"
              value={value.observedAt}
              onChange={(e) => update("observedAt", e.target.value)}
              required
            />
          </label>
          <label>
            Effective at
            <input
              type="datetime-local"
              value={value.effectiveAt}
              onChange={(e) => update("effectiveAt", e.target.value)}
              required
            />
          </label>
        </div>
      </fieldset>
      <fieldset>
        <legend>Governed policy and confidence</legend>
        <div className="form-grid">
          {textFields.slice(13).map(([key, label]) => (
            <label key={key}>
              {label}
              <input
                value={String(value[key])}
                onChange={(e) => update(key, e.target.value)}
                required
              />
            </label>
          ))}
          {scoreFields.map(([key, label]) => (
            <label key={key}>
              {label}
              <input
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={Number(value[key])}
                onChange={(e) => update(key, Number(e.target.value))}
              />
            </label>
          ))}
        </div>
      </fieldset>
      <div className="form-actions">
        <button type="submit" disabled={busy}>
          {busy ? "Submitting…" : "Submit assessment"}
        </button>
      </div>
    </form>
  );
}
