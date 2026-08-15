import Link from "next/link";

export function EntityResolutionLinkCard() {
  return (
    <section className="panel">
      <span className="eyebrow">Steward workspace</span>
      <h2>Entity Resolution Steward</h2>
      <p style={{ color: "var(--muted)" }}>
        Review multi-attribute evidence, preview policy outcomes, and record
        confirm/reject/unresolved/block-conflict decisions for supplier
        resolution cases.
      </p>
      <Link className="button" href="/ontology-studio/entity-resolution">
        Open Entity Resolution Steward
      </Link>
    </section>
  );
}
