import { JourneyLayers } from "../_components/architecture/journey-layers";
import { SupplierRiskRelationships } from "../_components/architecture/supplier-risk-relationships";
import { ScopeComparison } from "../_components/architecture/scope-comparison";
import { HowThisWorksDetails } from "../_components/architecture/how-this-works-details";

export default function Page() {
  return (
    <div className="max-w-3xl">
      <p className="eyebrow">Sample Dataset</p>
      <h1 style={{ marginTop: "0.25rem" }}>Architecture</h1>
      <p style={{ color: "var(--muted)", maxWidth: "42rem" }}>
        This page explains, in business terms, how the sample datasets behind
        the Supplier Risk demo become an explainable recommendation. It
        describes the working demo — not a live enterprise system.
      </p>

      <div style={{ marginTop: "2rem" }}>
        <JourneyLayers />
      </div>

      <div style={{ marginTop: "2rem" }}>
        <SupplierRiskRelationships />
      </div>

      <div style={{ marginTop: "2rem" }}>
        <ScopeComparison />
      </div>

      <div style={{ marginTop: "2rem" }}>
        <HowThisWorksDetails />
      </div>
    </div>
  );
}
