import type {
  EvidenceItem,
  MaterialEvaluationResult,
} from "@/lib/supply-chain-impact/contracts";

// WOW-I4-B1-R2 (operator: "excessive unused white space... between Risk
// Signal and ontology impact"): a single compact context caption, not an
// independent panel -- the real supplier name and severity now also
// appear as a structural chip on the Impact Intelligence chain's own
// Supplier hop (BusinessImpactPanel), so this caption's job is narrative
// context (the actual evidence citation) rather than duplicating a
// header. Same real fields, same props, as R1.
export function RiskSignalPanel({
  supplierName,
  evidence,
}: {
  supplierName: string;
  // Retained in the type so callers (including the standalone
  // accessibility test) need no change -- the severity/sourcing this
  // once drove now render as a structural chip on the Impact
  // Intelligence chain's own Supplier hop instead (BusinessImpactPanel).
  material: MaterialEvaluationResult | undefined;
  evidence: EvidenceItem[];
}) {
  const severityEvidence = evidence.find(
    (item) => item.predicate === "severity",
  );
  return (
    <div className="obs-sci-risk-strip" aria-label="Risk signal">
      <p className="obs-sci-risk-caption">
        <strong>{supplierName}</strong> —{" "}
        {severityEvidence ? (
          <>
            Reported as &ldquo;{severityEvidence.value}&rdquo; by{" "}
            {severityEvidence.source_system_name} on{" "}
            {new Date(severityEvidence.asserted_on).toLocaleString()}.
          </>
        ) : (
          "No governed severity evidence is available for this supplier."
        )}
      </p>
    </div>
  );
}
