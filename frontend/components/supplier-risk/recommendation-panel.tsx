import type { GovernedResult } from "@/lib/supplier-risk/contracts";
import { ReferenceList } from "./reference-list";
export function RecommendationPanel({ result }: { result: GovernedResult }) {
  return (
    <section className="panel recommendation">
      <div className="eyebrow">Governed recommendation</div>
      <h2>{result.recommendation ?? "No automated recommendation"}</h2>
      <p className="standing">
        <strong>
          {result.governance_standing ?? result.terminal_classification}
        </strong>{" "}
        · {result.actionable ? "Actionable" : "Not actionable"}
      </p>
      {result.safe_business_explanation && (
        <p>{result.safe_business_explanation}</p>
      )}
      {result.ontology_id && result.ontology_version && (
        <p className="eyebrow" style={{ marginTop: "0.5rem" }}>
          Powered by {result.ontology_id} v{result.ontology_version}
          {result.ontology_status ? ` · ${result.ontology_status}` : ""}
          {result.ontology_quality_score !== null
            ? ` · Quality ${(result.ontology_quality_score * 100).toFixed(0)}%`
            : ""}
        </p>
      )}
      {result.semantic_path && (
        <div className="conditions">
          <h3>Semantic path</h3>
          <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
            {result.semantic_path}
          </p>
        </div>
      )}
      {result.conditions.length > 0 && (
        <div className="conditions">
          <h3>Conditions</h3>
          <ul>
            {result.conditions.map((condition) => (
              <li key={condition}>
                {condition}{" "}
                {result.verified_conditions.includes(condition) ? (
                  <strong>Verified</strong>
                ) : (
                  <strong>Not verified</strong>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="reference-grid">
        <ReferenceList
          title="Evidence references"
          values={result.evidence_references}
        />
        <ReferenceList
          title="Provenance references"
          values={result.provenance_references}
        />
        <ReferenceList
          title="Produced records"
          values={result.produced_record_references}
        />
      </div>
      {result.policy_reference && (
        <p>
          <strong>Policy:</strong> {result.policy_reference}{" "}
          {result.policy_version} · {result.policy_rule}
        </p>
      )}
    </section>
  );
}
