import type { EvidenceItem } from "@/lib/supply-chain-impact/contracts";

// Renders exactly the governed fields the API actually returns -- no
// invented provenance, confidence, or verification status (CDD-016
// §13/§15). WOW-I4-B1-R1: a denser evidence matrix (fact/value/source+time
// as a compact grid, not a monotonous one-per-row stack), same four real
// fields as before. The empty state is now a deliberately visible,
// truthful statement rather than blank whitespace.
export function EvidencePanel({ evidence }: { evidence: EvidenceItem[] }) {
  return (
    <section className="panel" aria-label="Evidence">
      <div className="eyebrow">Evidence</div>
      <h2>Why should I trust this?</h2>
      {evidence.length === 0 ? (
        <p className="obs-sci-empty-evidence">
          No governed evidence is attached to this evaluation.
        </p>
      ) : (
        <ul className="obs-sci-evidence-list">
          {evidence.map((item, index) => (
            <li
              key={`${item.predicate}-${index}`}
              className="obs-sci-evidence-item"
            >
              <strong className="obs-sci-evidence-fact">
                {item.predicate}
              </strong>
              <span className="obs-sci-evidence-value">{item.value}</span>
              <span className="obs-sci-evidence-meta">
                {item.source_system_name} ·{" "}
                {new Date(item.asserted_on).toLocaleString()}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
