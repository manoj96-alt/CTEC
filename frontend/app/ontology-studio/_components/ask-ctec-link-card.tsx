import Link from "next/link";

export function AskCtecLinkCard() {
  return (
    <section className="panel">
      <span className="eyebrow">Ontology exploration</span>
      <h2>Ask CTEC</h2>
      <p style={{ color: "var(--muted)" }}>
        Ask a deterministic, read-only question about the governed
        enterprise ontology and see the exact evidence path behind the
        answer.
      </p>
      <Link className="button" href="/ontology-studio/ask">
        Open Ask CTEC
      </Link>
    </section>
  );
}
