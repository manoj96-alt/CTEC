import type { EvidenceItem } from "@/lib/supply-chain-impact/contracts";

// Renders exactly the governed fields the API actually returns -- no
// invented provenance (CDD-016 §13/§15).
export function EvidencePanel({ evidence }: { evidence: EvidenceItem[] }) {
  return (
    <section className="panel" aria-label="Evidence">
      <div className="eyebrow">Evidence</div>
      <h2>Why should I trust this?</h2>
      {evidence.length === 0 ? (
        <p>No governed evidence is attached to this evaluation.</p>
      ) : (
        <ul className="record-list">
          {evidence.map((item, index) => (
            <li key={`${item.predicate}-${index}`}>
              <strong>{item.predicate}</strong>: {item.value}
              <br />
              <small>
                Source: {item.source_system_name} · Asserted:{" "}
                {new Date(item.asserted_on).toLocaleString()}
              </small>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
