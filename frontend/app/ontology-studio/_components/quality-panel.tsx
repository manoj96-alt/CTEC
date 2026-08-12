import type { QualityScore } from "@/lib/ontology-studio/contracts";

export function QualityPanel({ quality }: { quality: QualityScore }) {
  return (
    <section className="panel" style={{ marginTop: "1.5rem" }}>
      <p className="eyebrow">Deterministic ontology quality assessment</p>
      <h2 style={{ marginTop: "0.25rem" }}>
        Overall score: {(quality.overall_score * 100).toFixed(0)}%
      </h2>
      <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
        {quality.method}
      </p>

      <div
        style={{
          marginTop: "1rem",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(14rem, 1fr))",
          gap: "0.5rem",
        }}
      >
        {quality.dimensions.map((dimension) => (
          <div key={dimension.dimension} style={{ fontSize: "0.85rem" }}>
            <p style={{ fontWeight: 700 }}>
              {dimension.passed ? "✓" : "✗"}{" "}
              {dimension.dimension.replaceAll("_", " ")} (
              {(dimension.score * 100).toFixed(0)}%)
            </p>
            <p style={{ color: "var(--muted)" }}>{dimension.explanation}</p>
          </div>
        ))}
      </div>

      <p style={{ marginTop: "0.75rem", fontSize: "0.85rem" }}>
        <strong>Passed:</strong> {quality.passed_checks.join(", ") || "none"}
      </p>
      <p style={{ fontSize: "0.85rem" }}>
        <strong>Failed:</strong> {quality.failed_checks.join(", ") || "none"}
      </p>
    </section>
  );
}
