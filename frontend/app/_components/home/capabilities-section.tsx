const CAPABILITIES = [
  {
    title: "Ontology construction",
    description:
      "Technical records from separate systems are mapped into one connected, business-readable model.",
  },
  {
    title: "Connected impact analysis",
    description:
      "Relationships reveal which materials, products, facilities, and revenue are affected by an event — not just the event itself.",
  },
  {
    title: "Explainable decision policies",
    description:
      "Recommendations come from explicit, deterministic rules applied to evidence — not an opaque model.",
  },
  {
    title: "Human approval",
    description:
      "Every recommendation is proposed, never applied automatically. A person approves or rejects it.",
  },
] as const;

export function CapabilitiesSection() {
  return (
    <section className="mt-16">
      <p className="eyebrow">What CTEC does</p>
      <h2 className="mt-2 text-2xl font-bold tracking-tight">
        Major capabilities
      </h2>
      <div
        className="mt-6 grid gap-4"
        style={{ gridTemplateColumns: "repeat(auto-fit, minmax(14rem, 1fr))" }}
      >
        {CAPABILITIES.map((capability) => (
          <div key={capability.title} className="panel" style={{ margin: 0 }}>
            <p className="font-bold">{capability.title}</p>
            <p className="mt-2 text-sm" style={{ color: "var(--muted)" }}>
              {capability.description}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
