import Link from "next/link";

export function ActivationCard({ version }: { version: string }) {
  return (
    <section
      className="panel"
      style={{ marginTop: "1.5rem", textAlign: "center" }}
    >
      <p className="eyebrow">Activation</p>
      <h2 style={{ marginTop: "0.25rem" }}>Supplier Risk Analysis</h2>
      <p
        style={{
          color: "var(--muted)",
          maxWidth: "32rem",
          margin: "0.5rem auto 0",
        }}
      >
        This application is powered by Supplier Risk Enterprise Ontology v
        {version}.
      </p>
      <Link
        href="/supplier-risk"
        className="button"
        style={{ marginTop: "0.75rem" }}
      >
        Open Supplier Risk Application
      </Link>
    </section>
  );
}
