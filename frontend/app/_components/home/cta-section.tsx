import Link from "next/link";

// NOTE: A secondary "View Sample Dataset" CTA is deliberately deferred here.
// /dataset is still a placeholder page (Dataset is a later item in the
// menu-by-menu sequence), and linking to it now would present an unfinished
// experience as complete. This CTA will be added when the Dataset menu item
// is built.
export function CtaSection() {
  return (
    <section className="mt-16">
      <div className="panel" style={{ textAlign: "center" }}>
        <p className="text-lg font-bold">See it work on a real scenario</p>
        <p className="mt-2" style={{ color: "var(--muted)" }}>
          Walk through the full import-to-recommendation journey with a sample
          supplier disruption.
        </p>
        <Link
          href="/demo/supplier-risk"
          className="button"
          style={{ marginTop: "1.25rem" }}
        >
          Explore Supplier Risk
        </Link>
      </div>
    </section>
  );
}
