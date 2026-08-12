const STAGES = [
  {
    label: "Import Data",
    description: "Source records are imported from sample datasets.",
  },
  {
    label: "Map Schema",
    description: "Technical fields are mapped to business concepts.",
  },
  {
    label: "Explore Ontology",
    description:
      "Connected relationships reveal business impact — which materials, products, facilities, and revenue are affected.",
  },
  {
    label: "Decision Flow",
    description: "Explicit, deterministic rules evaluate the evidence.",
  },
  {
    label: "Recommendation",
    description: "The recommendation is presented for human review.",
  },
] as const;

export function JourneySection() {
  return (
    <section className="mt-16">
      <p className="eyebrow">The journey</p>
      <h2 className="mt-2 text-2xl font-bold tracking-tight">
        From fragmented data to explainable decisions
      </h2>
      <ol
        className="mt-6 grid gap-4"
        style={{ gridTemplateColumns: "repeat(auto-fit, minmax(11rem, 1fr))" }}
      >
        {STAGES.map((stage, index) => (
          <li key={stage.label} className="panel" style={{ margin: 0 }}>
            <p
              className="text-xs font-bold uppercase tracking-widest"
              style={{ color: "var(--accent)" }}
            >
              Stage {index + 1}
            </p>
            <p className="mt-1 font-bold">{stage.label}</p>
            <p className="mt-2 text-sm" style={{ color: "var(--muted)" }}>
              {stage.description}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
