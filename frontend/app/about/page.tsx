const STAGES = [
  "Import Data",
  "Map Schema",
  "Explore Ontology",
  "Decision Flow",
  "Recommendation",
] as const;

export default function Page() {
  return (
    <div className="max-w-3xl">
      <p className="eyebrow">About This Demonstration</p>
      <h1 style={{ marginTop: "0.25rem" }}>About</h1>

      <section style={{ marginTop: "2rem" }}>
        <h2>What CTEC is</h2>
        <p style={{ color: "var(--muted)" }}>
          CTEC is an ontology-backed decision-support prototype and
          demonstration — not a production platform. It shows one way connected
          data can support an explainable, human-reviewed recommendation.
        </p>
      </section>

      <section style={{ marginTop: "1.5rem" }}>
        <h2>The problem demonstrated</h2>
        <p style={{ color: "var(--muted)" }}>
          Supplier, material, product, facility, and revenue data typically live
          in separate systems. This demonstration connects them so that when a
          disruption occurs, the affected path — and the business impact along
          it — can be traced rather than pieced together by hand.
        </p>
      </section>

      <section style={{ marginTop: "1.5rem" }}>
        <h2>Who may find it useful</h2>
        <p style={{ color: "var(--muted)" }}>
          This demonstration may be relevant to supply-chain leaders, data and
          governance practitioners, and product or technology teams evaluating
          ontology-and-rules-based decision support — not a claim of current
          customers or adoption.
        </p>
      </section>

      <section style={{ marginTop: "1.5rem" }}>
        <h2>What the walkthrough demonstrates</h2>
        <p style={{ color: "var(--muted)" }}>
          The walkthrough demonstrates how a supplier disruption can be
          connected through controlled sample data to an evidence-supported
          recommendation for human review. It uses seven controlled sample CSV
          fixtures, and moves through five established stages:
        </p>
        <ol
          style={{
            margin: "0.75rem 0 0",
            paddingLeft: "1.4rem",
            fontSize: "0.95rem",
          }}
        >
          {STAGES.map((stage) => (
            <li key={stage}>{stage}</li>
          ))}
        </ol>
      </section>

      <section style={{ marginTop: "1.5rem" }}>
        <h2>Guiding principles</h2>
        <ul style={{ paddingLeft: "1.2rem", color: "var(--muted)" }}>
          <li>
            Recommendation factors and rule conditions reference sample fixture
            filenames and row indexes.
          </li>
          <li>
            Recommendation conditions are evaluated by deterministic rules—not
            AI, LLM, or agent reasoning.
          </li>
          <li>
            Impact is calculated from an ontology built out of connected sample
            records.
          </li>
          <li>
            Approve or Reject records one reviewer decision in the current
            rendered demo session. No operational action is executed and no
            enterprise system is updated.
          </li>
        </ul>
      </section>

      <section style={{ marginTop: "1.5rem" }}>
        <h2>Current demonstration boundary</h2>
        <p style={{ color: "var(--muted)" }}>
          This demonstration does not provide live enterprise connectivity,
          persistent decision or evidence storage, operational execution,
          enterprise authentication or authorization, or AI, LLM, or agent
          decision-making.
        </p>
      </section>
    </div>
  );
}
