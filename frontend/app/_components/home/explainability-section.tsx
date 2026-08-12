export function ExplainabilitySection() {
  return (
    <section className="mt-16">
      <p className="eyebrow">Explainability and control</p>
      <h2 className="mt-2 text-2xl font-bold tracking-tight">
        Deterministic rules, human decisions
      </h2>
      <p className="mt-4 max-w-2xl leading-7" style={{ color: "var(--muted)" }}>
        CTEC does not use an opaque model to decide what happens next.
        Recommendation factors and rule conditions reference sample fixture
        filenames and row indexes. The recommendation is presented for human
        review — Approve or Reject records one reviewer decision in the current
        rendered demo session. No operational action is executed and no
        enterprise system is updated.
      </p>
    </section>
  );
}
