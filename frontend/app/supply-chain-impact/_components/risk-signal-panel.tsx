import type { EvidenceItem, MaterialEvaluationResult } from "@/lib/supply-chain-impact/contracts";

function severityLabel(highSeverityDisruption: boolean | null): string {
  if (highSeverityDisruption === null) return "Unknown";
  return highSeverityDisruption ? "High severity" : "Not high severity";
}

export function RiskSignalPanel({
  supplierName,
  material,
  evidence,
}: {
  supplierName: string;
  material: MaterialEvaluationResult | undefined;
  evidence: EvidenceItem[];
}) {
  const severityEvidence = evidence.find((item) => item.predicate === "severity");
  return (
    <section className="panel" aria-label="Risk signal">
      <div className="eyebrow">Risk signal</div>
      <h2>{supplierName}</h2>
      <p className="standing">
        <strong>{severityLabel(material?.high_severity_disruption ?? null)}</strong>
      </p>
      {severityEvidence ? (
        <p>
          Reported as &ldquo;{severityEvidence.value}&rdquo; by {severityEvidence.source_system_name}
          {" "}on {new Date(severityEvidence.asserted_on).toLocaleString()}.
        </p>
      ) : (
        <p>No governed severity evidence is available for this supplier.</p>
      )}
    </section>
  );
}
