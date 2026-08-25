import Link from "next/link";

export default function Page() {
  return (
    <div className="max-w-5xl">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Intelligence</span>
          <h1>Supplier Risk</h1>
          <p>
            Governed supplier risk assessment and supply chain impact decisions,
            backed by CTEC&apos;s existing evidence and decision engines.
          </p>
        </div>
      </div>
      <section className="panel">
        <span className="eyebrow">Assessment workspace</span>
        <h2>Supplier Risk Assessments</h2>
        <p style={{ color: "var(--muted)" }}>
          Track governed assessments and the action each recommendation permits.
        </p>
        <Link className="button" href="/supplier-risk">
          Open Supplier Risk Assessments
        </Link>
      </section>
      <section className="panel" style={{ marginTop: "1.5rem" }}>
        <span className="eyebrow">Decision workspace</span>
        <h2>Supply Chain Impact</h2>
        <p style={{ color: "var(--muted)" }}>
          Evaluate governed supply chain impact and mitigation recommendations
          for a supplier disruption scenario.
        </p>
        <Link className="button" href="/supply-chain-impact">
          Open Supply Chain Impact
        </Link>
      </section>
    </div>
  );
}
