import type {
  EvidenceItem,
  ImpactSummary,
} from "@/lib/supply-chain-impact/contracts";

function currency(value: string | undefined): string {
  if (!value) return "unknown";
  const amount = Number(value);
  if (Number.isNaN(amount)) return value;
  return amount.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}

function materialityLabel(revenueMateriality: boolean | null): string {
  if (revenueMateriality === null) return "Unknown";
  return revenueMateriality
    ? "Exceeds materiality threshold"
    : "Below materiality threshold";
}

function singleSourceLabel(singleSourceExposure: boolean | null): string {
  if (singleSourceExposure === null) return "Unknown";
  return singleSourceExposure ? "Single-sourced" : "Multi-sourced";
}

// Explanatory visualization only -- every node/edge below comes directly
// from `impact` (already server-traversed); no traversal, inference, or
// new ontology query happens here (CDD-016 §11).
export function BusinessImpactPanel({
  impact,
  singleSourceExposure,
  revenueMateriality,
  evidence,
}: {
  impact: ImpactSummary;
  singleSourceExposure: boolean | null;
  revenueMateriality: boolean | null;
  evidence: EvidenceItem[];
}) {
  const revenueEvidence = evidence.find(
    (item) => item.predicate === "annualRevenueUsd",
  );
  return (
    <section className="panel" aria-label="Business impact">
      <div className="eyebrow">Business impact</div>
      <h2>Why it matters</h2>
      <dl className="status-grid">
        <dt>Sourcing</dt>
        <dd>{singleSourceLabel(singleSourceExposure)}</dd>
        <dt>Revenue exposure</dt>
        <dd>
          {materialityLabel(revenueMateriality)}
          {revenueEvidence ? ` (${currency(revenueEvidence.value)})` : ""}
        </dd>
      </dl>
      <div className="conditions">
        <h3>Dependency chain</h3>
        <ol className="timeline">
          <li>{impact.supplier_name}</li>
          {impact.materials.map((material) => (
            <li key={material.material_entity_id}>{material.material_name}</li>
          ))}
          {impact.products.map((product) => (
            <li key={product.entity_id}>{product.entity_name}</li>
          ))}
          {impact.facilities.map((facility) => (
            <li key={facility.entity_id}>{facility.entity_name}</li>
          ))}
        </ol>
      </div>
      {impact.revenue_exposures.length > 0 && (
        <p>
          Revenue exposure recorded against:{" "}
          {impact.revenue_exposures.map((item) => item.entity_name).join(", ")}
        </p>
      )}
    </section>
  );
}
