import type {
  EvidenceItem,
  MaterialEvaluationResult,
} from "@/lib/supply-chain-impact/contracts";

function severityLabel(highSeverityDisruption: boolean | null): string {
  if (highSeverityDisruption === null) return "Unknown";
  return highSeverityDisruption ? "High severity" : "Not high severity";
}

// WOW-I4-B1-R1 (operator visual rejection): no longer its own `.panel` --
// a compact header strip inside the shared "Impact intelligence" surface
// in page.tsx, the first step of the Risk -> Ontology impact -> Revenue
// flow. Same real fields as before, denser presentation only.
export function RiskSignalPanel({
  supplierName,
  material,
  evidence,
}: {
  supplierName: string;
  material: MaterialEvaluationResult | undefined;
  evidence: EvidenceItem[];
}) {
  const severityEvidence = evidence.find(
    (item) => item.predicate === "severity",
  );
  return (
    <div className="obs-sci-risk-strip" aria-label="Risk signal">
      <div className="obs-sci-risk-strip-head">
        <span className="obs-sci-risk-label">Risk signal</span>
        <span className="obs-sci-risk-supplier">{supplierName}</span>
        <span className="status-tag">
          {severityLabel(material?.high_severity_disruption ?? null)}
        </span>
      </div>
      {severityEvidence ? (
        <p className="obs-sci-evidence-meta">
          Reported as &ldquo;{severityEvidence.value}&rdquo; by{" "}
          {severityEvidence.source_system_name} on{" "}
          {new Date(severityEvidence.asserted_on).toLocaleString()}.
        </p>
      ) : (
        <p>No governed severity evidence is available for this supplier.</p>
      )}
    </div>
  );
}
