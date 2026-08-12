import Link from "next/link";

const STAGES = [
  {
    label: "Import Data",
    preview: "The seven controlled sample CSV files are loaded.",
  },
  {
    label: "Map Schema",
    preview: "Fields are mapped to business concepts using sample mappings.",
  },
  {
    label: "Explore Ontology",
    preview:
      "Records are connected into the sample ontology, and impact is calculated.",
  },
  {
    label: "Decision Flow",
    preview: "Deterministic demo rules are evaluated against the facts.",
  },
  {
    label: "Recommendation",
    preview: "You'll see the proposed action and can Approve or Reject it.",
  },
] as const;

export default function Page() {
  return (
    <div className="max-w-3xl">
      <p className="eyebrow">Working Demo</p>
      <h1 style={{ marginTop: "0.25rem" }}>Prototype</h1>
      <p style={{ color: "var(--muted)", maxWidth: "42rem" }}>
        This page previews and launches the working Supplier Risk walkthrough.
        It is not a separate simulator — there is one working demo, and this
        page orients you to it before you try it.
      </p>

      <section style={{ marginTop: "2rem" }}>
        <p className="eyebrow">Five-stage walkthrough preview</p>
        <h2 style={{ marginTop: "0.25rem" }}>What you&apos;ll walk through</h2>
        <ol
          style={{
            margin: "1rem 0 0",
            paddingLeft: "1.4rem",
            display: "grid",
            gap: "0.75rem",
          }}
        >
          {STAGES.map((stage) => (
            <li key={stage.label} className="panel" style={{ margin: 0 }}>
              <p style={{ fontWeight: 700, marginBottom: "0.25rem" }}>
                {stage.label}
              </p>
              <p style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
                {stage.preview}
              </p>
            </li>
          ))}
        </ol>
      </section>

      <section className="panel" style={{ marginTop: "2rem" }}>
        <p className="eyebrow">What to expect</p>
        <ul
          style={{
            margin: "0.75rem 0 0",
            paddingLeft: "1.2rem",
            fontSize: "0.9rem",
          }}
        >
          <li>Controlled sample data — not a live enterprise connection.</li>
          <li>
            Deterministic demo rules, not AI or LLM reasoning, decide the
            recommendation.
          </li>
          <li>
            Recommendation factors and rule conditions reference sample fixture
            filenames and row indexes.
          </li>
          <li>
            The recommendation is presented for human review. Approve or Reject
            records one reviewer decision in the current demo session — no
            operational action is executed and no enterprise system is updated.
          </li>
          <li>Reset Demo clears the current in-memory walkthrough state.</li>
        </ul>
      </section>

      <section
        className="panel"
        style={{ marginTop: "2rem", textAlign: "center" }}
      >
        <p style={{ fontWeight: 700 }}>Ready to try it?</p>
        <Link
          href="/demo/supplier-risk"
          className="button"
          style={{ marginTop: "0.75rem" }}
        >
          Launch the Supplier Risk Walkthrough
        </Link>
      </section>
    </div>
  );
}
