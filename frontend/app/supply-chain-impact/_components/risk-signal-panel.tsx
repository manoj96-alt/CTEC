import type {
  EvidenceItem,
  MaterialEvaluationResult,
} from "@/lib/supply-chain-impact/contracts";

function currency(value: string | undefined): string | null {
  if (!value) return null;
  const amount = Number(value);
  if (Number.isNaN(amount)) return null;
  return amount.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}

function severityLabel(highSeverityDisruption: boolean | null): string {
  if (highSeverityDisruption === true) return "High severity";
  if (highSeverityDisruption === false) return "Not high severity";
  return "Severity unknown";
}

function sourcingLabel(singleSourceExposure: boolean | null): string {
  if (singleSourceExposure === true) return "Single-sourced";
  if (singleSourceExposure === false) return "Multi-sourced";
  return "Sourcing unknown";
}

// WOW-I4-B1-R3 (operator: "the page should communicate WHAT IS AT RISK in
// approximately five seconds"): a compact risk banner sitting directly on
// the dark Observatory canvas -- not another white card -- built entirely
// from real fields already available on `material`/`evidence`. No new
// fetch, no computed business conclusion: severity/sourcing come straight
// from the same governed tri-state facts BusinessImpactPanel's chain
// already renders, and the exposure figure is the same real
// `annualRevenueUsd` assertion value used throughout this route.
// `governanceStanding` is the identical top-level field
// HumanAuthorityBanner renders lower on the page -- threaded here only
// for a truthful "Human decision required" cue, never a second/competing
// recommendation (the actual outcome is revealed only in the Governed
// Decision block below).
export function RiskSignalPanel({
  supplierName,
  material,
  evidence,
  governanceStanding = null,
}: {
  supplierName: string;
  material: MaterialEvaluationResult | undefined;
  evidence: EvidenceItem[];
  governanceStanding?: string | null;
}) {
  const severityEvidence = evidence.find(
    (item) => item.predicate === "severity",
  );
  const revenueEvidence = evidence.find(
    (item) => item.predicate === "annualRevenueUsd",
  );
  const revenue = currency(revenueEvidence?.value);
  const highSeverity = material?.high_severity_disruption ?? null;

  return (
    <div className="obs-sci-risk-banner" aria-label="Risk signal">
      <div className="obs-sci-risk-banner-row">
        <span
          className={
            highSeverity === true
              ? "status-tag obs-sci-risk-tag obs-sci-risk-tag--conflict"
              : "status-tag obs-sci-risk-tag"
          }
        >
          {severityLabel(highSeverity)}
        </span>
        <span className="obs-sci-risk-supplier">{supplierName}</span>
        {revenue && (
          <span className="obs-sci-risk-exposure">{revenue} exposure</span>
        )}
      </div>
      <div className="obs-sci-risk-banner-row obs-sci-risk-banner-row--sub">
        <span className="obs-sci-risk-sourcing">
          {sourcingLabel(material?.single_source_exposure ?? null)}
        </span>
        {governanceStanding === "HUMAN_APPROVAL_REQUIRED" && (
          <span className="obs-sci-risk-authority">
            Human decision required
          </span>
        )}
      </div>
      <p className="obs-sci-risk-caption">
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
