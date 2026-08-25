import Link from "next/link";
import { CapabilityStatusBadge } from "@/components/design-system/capability-status-badge";
import { PageHeader } from "@/components/design-system/page-header";

// Capability / governance / status presentation ONLY (CDD-033 §15/§17,
// X-D2, X-AA-D1; Artifact Authorization §12). This page must never: query
// Gate T runtime internals, expose or create any Gate T API, fabricate
// FIT/STALE/CONFLICTING records or evidence, or imply generalized Data
// Quality. There is deliberately no "Run" / "Evaluate" / "Refresh Fitness"
// action anywhere on this page -- no such live execution is authorized.
export default function Page() {
  return (
    <div className="max-w-5xl">
      <PageHeader
        eyebrow="Quality"
        title="Evidence Fitness"
        description="Gate T's governed evidence-fitness evaluation, presented here as capability, governance, and status information only."
        action={<CapabilityStatusBadge status="AVAILABLE_BUT_DISCONNECTED" />}
      />

      <section className="panel">
        <span className="eyebrow">Status</span>
        <h2>Live evaluation is not available in this workspace</h2>
        <p style={{ color: "var(--muted)" }}>
          CTEC evaluates source evidence fitness for information already
          resolved into the ontology as a governed backend capability. That
          evaluation is not exposed through any authorized Gate X frontend
          contract in this release, so this page cannot show, run, or refresh a
          live fitness result for any supplier or information element.
        </p>
      </section>

      <section className="panel" style={{ marginTop: "1.5rem" }}>
        <span className="eyebrow">Governed vocabulary</span>
        <h2>Fitness statuses</h2>
        <p style={{ color: "var(--muted)" }}>
          When exposed, each information element&apos;s evidence is classified
          into one of three governed statuses:
        </p>
        <dl style={{ marginTop: "0.75rem" }}>
          <dt style={{ fontWeight: 700 }}>FIT</dt>
          <dd style={{ color: "var(--muted)" }}>
            The available evidence satisfies the information element&apos;s
            requirement.
          </dd>
          <dt style={{ fontWeight: 700, marginTop: "0.5rem" }}>STALE</dt>
          <dd style={{ color: "var(--muted)" }}>
            The available evidence is out of date and requires refresh.
          </dd>
          <dt style={{ fontWeight: 700, marginTop: "0.5rem" }}>CONFLICTING</dt>
          <dd style={{ color: "var(--muted)" }}>
            Multiple sources disagree and require review.
          </dd>
        </dl>
      </section>

      <section className="panel" style={{ marginTop: "1.5rem" }}>
        <span className="eyebrow">Related, not connected</span>
        <h2>Generalized Data Quality</h2>
        <p style={{ color: "var(--muted)" }}>
          Evidence Fitness is a distinct, already-governed capability (CDD-031)
          and is not part of, and does not imply, the separate generalized Data
          Quality capability marked Planned on the Quality landing page.
        </p>
      </section>

      <p style={{ marginTop: "1.5rem" }}>
        <Link href="/quality">Back to Quality</Link>
      </p>
    </div>
  );
}
