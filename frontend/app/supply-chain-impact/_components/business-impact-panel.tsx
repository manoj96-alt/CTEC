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

// WOW-I4-B1-R1: hop-grouped, not per-edge -- unchanged truth boundary from
// R1 (CDD-085 §5/§7.2). `impact.materials/products/facilities/
// revenue_exposures` are already deduplicated, merged arrays server-side
// -- the exposed contract does not preserve which product came from which
// material. Rendered inside a dark canvas sub-surface (reusing the exact
// --obs-* tokens Ontology Explorer's own node/edge treatment already
// established -- --obs-surface-elevated chips, --obs-intelligence
// connectors -- as tokens only, no Explorer component imported), so this
// reads as an ontology-grounded visualization rather than plain text
// columns, per the operator's explicit comparison to Ontology Explorer's
// quality bar. Still semantic heading-plus-list markup throughout, so it
// remains inherently accessible without a separate duplicate fallback.
function DependencyChain({ impact }: { impact: ImpactSummary }) {
  const hops: Array<{ label: string; items: string[] }> = [
    { label: "Material", items: impact.materials.map((m) => m.material_name) },
    { label: "Product", items: impact.products.map((p) => p.entity_name) },
    { label: "Facility", items: impact.facilities.map((f) => f.entity_name) },
  ].filter((hop) => hop.items.length > 0);

  if (hops.length === 0) {
    return (
      <p className="obs-sci-chain-caption">
        No governed dependency structure is available for this supplier.
      </p>
    );
  }

  return (
    <div className="obs-sci-chain-canvas">
      <div className="obs-sci-chain" role="group" aria-label="Ontology impact">
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
                <li className="obs-sci-chain-chip" key={item}>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

// Explanatory visualization only -- every node/edge below comes directly
// from `impact` (already server-traversed); no traversal, inference, or
// new ontology query happens here (CDD-016 §11). WOW-I4-B1-R1: no longer
// its own `.panel` -- the second and third steps of the Risk -> Ontology
// impact -> Revenue flow inside the shared "Impact intelligence" surface.
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
    <div aria-label="Business impact" className="obs-sci-impact-body">
      <div className="obs-sci-impact-badges">
        <span className="status-tag">
          {singleSourceLabel(singleSourceExposure)}
        </span>
        <span className="status-tag">
          {materialityLabel(revenueMateriality)}
        </span>
      </div>
      <p className="obs-sci-chain-caption">
        Impact grouped by governed ontology relationship hop -- not a specific
        item-to-item traced path.
      </p>
      <DependencyChain impact={impact} />
      {impact.revenue_exposures.length > 0 && (
        <div className="obs-sci-revenue">
          <span className="obs-sci-revenue-label">
            Revenue exposure recorded against{" "}
            {impact.revenue_exposures
              .map((item) => item.entity_name)
              .join(", ")}
          </span>
          {revenueEvidence && (
            <span className="obs-sci-revenue-value">
              {currency(revenueEvidence.value)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
