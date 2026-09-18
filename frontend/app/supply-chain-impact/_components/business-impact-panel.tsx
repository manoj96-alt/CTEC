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

// WOW-I4-B1 (CDD-085 §7.2): hop-grouped, not per-edge. `impact.materials/
// products/facilities/revenue_exposures` are already deduplicated, merged
// arrays server-side (backend/app/application/supply_chain_impact_api.py)
// -- the exposed contract does not preserve which product came from which
// material. Grouping by relationship hop is truthful; drawing a specific
// item-to-item line would not be, so this stays semantic
// heading-plus-list markup (real, always-accessible text), never a
// graph/diagram library or an implied one-to-one edge.
function DependencyChain({ impact }: { impact: ImpactSummary }) {
  const hops: Array<{ label: string; items: string[] }> = [
    { label: "Supplier", items: [impact.supplier_name] },
    {
      label: "Materials",
      items: impact.materials.map((m) => m.material_name),
    },
    { label: "Products", items: impact.products.map((p) => p.entity_name) },
    {
      label: "Facilities & revenue exposure",
      items: [
        ...impact.facilities.map((f) => f.entity_name),
        ...impact.revenue_exposures.map((r) => r.entity_name),
      ],
    },
  ].filter((hop) => hop.items.length > 0);

  return (
    <div className="obs-sci-chain" role="group" aria-label="Dependency chain">
      {hops.map((hop, index) => (
        <div className="obs-sci-chain-hop" key={hop.label}>
          {index > 0 && (
            <span className="obs-sci-chain-arrow" aria-hidden="true">
              →
            </span>
          )}
          <div className="obs-sci-chain-hop-label">{hop.label}</div>
          <ul>
            {hop.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
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
        <p className="obs-sci-chain-caption">
          Grouped by real ontology relationship hop, not a specific item-to-item
          traced path.
        </p>
        <DependencyChain impact={impact} />
      </div>
    </section>
  );
}
