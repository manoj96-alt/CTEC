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

function severityLabel(highSeverityDisruption: boolean | null): string {
  if (highSeverityDisruption === null) return "Unknown";
  return highSeverityDisruption ? "High severity" : "Not high severity";
}

interface Hop {
  label: string;
  items: string[];
  terminal?: boolean;
}

// WOW-I4-B1-R2 (operator: "Supplier and Revenue Exposure are outside the
// visual chain... this weakens Noetva's core differentiator"): the FULL
// real hop sequence -- Supplier -> Material -> Product -> Facility ->
// Revenue Exposure -- using only fields already present on `impact`/
// `evidence` (no new API field, no new traversal). Severity/sourcing
// attach to the Supplier hop; materiality + the real revenue figure
// attach to the terminal Revenue Exposure hop -- every real fact now
// lives inside the one composition instead of floating as separate
// badges/metrics beside it. Still hop-grouped, not per-edge (CDD-085
// §5/§7.2 truth boundary unchanged): the inline arrows between hop
// GROUPS are presentation/progression only, never a claimed backend-
// proven item-to-item traced edge -- the caption states this explicitly.
function DependencyChain({
  impact,
  highSeverityDisruption,
  singleSourceExposure,
  revenueMateriality,
  revenueValue,
}: {
  impact: ImpactSummary;
  highSeverityDisruption: boolean | null;
  singleSourceExposure: boolean | null;
  revenueMateriality: boolean | null;
  revenueValue: string | undefined;
}) {
  const hops: Hop[] = [
    { label: "Supplier", items: [impact.supplier_name] },
    { label: "Material", items: impact.materials.map((m) => m.material_name) },
    { label: "Product", items: impact.products.map((p) => p.entity_name) },
    { label: "Facility", items: impact.facilities.map((f) => f.entity_name) },
    {
      label: "Revenue exposure",
      items: impact.revenue_exposures.map((r) => r.entity_name),
      terminal: true,
    },
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
          <div
            className={
              hop.terminal
                ? "obs-sci-chain-hop obs-sci-chain-hop--terminal"
                : "obs-sci-chain-hop"
            }
            key={hop.label}
          >
            {index > 0 && (
              <span className="obs-sci-chain-arrow" aria-hidden="true">
                →
              </span>
            )}
            <div className="obs-sci-chain-hop-label">{hop.label}</div>
            <ul>
              {hop.items.map((item) => (
                <li className="obs-sci-chain-chip" key={item}>
                  <span>{item}</span>
                  {hop.label === "Supplier" && (
                    <span className="obs-sci-chain-chip-tags">
                      <span className="status-tag">
                        {severityLabel(highSeverityDisruption)}
                      </span>
                      <span className="status-tag">
                        {singleSourceLabel(singleSourceExposure)}
                      </span>
                    </span>
                  )}
                  {hop.terminal && (
                    <span className="obs-sci-chain-chip-tags">
                      <span className="status-tag">
                        {materialityLabel(revenueMateriality)}
                      </span>
                      {revenueValue && (
                        <span className="obs-sci-chain-chip-value">
                          {currency(revenueValue)}
                        </span>
                      )}
                    </span>
                  )}
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
// new ontology query happens here (CDD-016 §11). WOW-I4-B1-R2: this is
// now the single Impact Intelligence composition -- Supplier through
// Material/Product/Facility to Revenue Exposure, one dark canvas, no
// separate badge row and no metric floating below it.
export function BusinessImpactPanel({
  impact,
  singleSourceExposure,
  revenueMateriality,
  evidence,
  highSeverityDisruption = null,
}: {
  impact: ImpactSummary;
  singleSourceExposure: boolean | null;
  revenueMateriality: boolean | null;
  evidence: EvidenceItem[];
  highSeverityDisruption?: boolean | null;
}) {
  const revenueEvidence = evidence.find(
    (item) => item.predicate === "annualRevenueUsd",
  );
  return (
    <div aria-label="Business impact" className="obs-sci-impact-body">
      <p className="obs-sci-chain-caption">
        Impact grouped by governed ontology relationship hop -- not a specific
        item-to-item traced path.
      </p>
      <DependencyChain
        impact={impact}
        highSeverityDisruption={highSeverityDisruption}
        singleSourceExposure={singleSourceExposure}
        revenueMateriality={revenueMateriality}
        revenueValue={revenueEvidence?.value}
      />
    </div>
  );
}
