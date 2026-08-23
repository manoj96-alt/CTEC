import Link from "next/link";

export function OntologyModelingLinkCard() {
  return (
    <section className="panel">
      <span className="eyebrow">Ontology modeling workspace</span>
      <h2>Governed Visual Ontology Modeling</h2>
      <p style={{ color: "var(--muted)" }}>
        Propose a net-new Concept or Relationship, review it, and -- once
        approved by an authorized governance principal -- publish it as the
        initial canonical representation of a new ontology object. Modification
        of an existing Concept or Relationship is not yet supported.
      </p>
      <Link className="button" href="/ontology-studio/ontology-modeling">
        Open Ontology Modeling
      </Link>
    </section>
  );
}
