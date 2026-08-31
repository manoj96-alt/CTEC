import Link from "next/link";
import { CapabilityStatusBadge } from "@/components/design-system/capability-status-badge";
import { PageHeader } from "@/components/design-system/page-header";
import { CommandCenter } from "./_components/command-center";

// CDD-045 §12/§16, CDD-033 OQI7 companion amendment: the four
// "Rules"/"Findings"/"DQ Impact"/"Remediation" PLANNED placeholders are
// superseded by the live Ontology Quality Intelligence Command Center --
// the closed, governed OQI1-6 capability family CDD-045 names precisely.
// Evidence Fitness keeps its own separate, unchanged route/section.
export default function Page() {
  return (
    <div className="max-w-5xl">
      <PageHeader
        eyebrow="Quality"
        title="Ontology Quality Intelligence"
        description="Can I rely on my enterprise knowledge, where is it at risk, why does it matter, and what is being done about it?"
      />

      <CommandCenter />

      <section className="panel" style={{ marginTop: "1.5rem" }}>
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
    </div>
  );
}
