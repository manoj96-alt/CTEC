import Link from "next/link";
import { CapabilityStatusBadge } from "@/components/design-system/capability-status-badge";
import { PageHeader } from "@/components/design-system/page-header";

// Status/link cards only -- no capability detail of any kind lives on this
// page (CDD-033 §15/§18, X-D2, X-AA-D1). Evidence Fitness gets its own
// dedicated route (see app/quality/evidence-fitness/page.tsx); the
// generalized Data Quality concepts below are PLANNED only, with no active
// route and no interaction affordance, per AA §14.
const PLANNED_CONCEPTS = ["Rules", "Findings", "DQ Impact", "Remediation"];

export default function Page() {
  return (
    <div className="max-w-5xl">
      <PageHeader eyebrow="Quality" title="Quality" />

      <section className="panel">
        <span className="eyebrow">Quality</span>
        <h2>Evidence Fitness</h2>
        <div style={{ marginTop: "0.5rem" }}>
          <CapabilityStatusBadge status="AVAILABLE_BUT_DISCONNECTED" />
        </div>
        <div style={{ marginTop: "0.75rem" }}>
          <Link className="button" href="/quality/evidence-fitness">
            View Evidence Fitness
          </Link>
        </div>
      </section>

      <div
        style={{
          marginTop: "1.5rem",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(14rem, 1fr))",
          gap: "1rem",
        }}
      >
        {PLANNED_CONCEPTS.map((name) => (
          <section key={name} className="panel" style={{ opacity: 0.6 }}>
            <span className="eyebrow">Quality — Planned</span>
            <h3 style={{ marginTop: "0.25rem" }}>{name}</h3>
            <div style={{ marginTop: "0.5rem" }}>
              <CapabilityStatusBadge status="PLANNED" />
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
