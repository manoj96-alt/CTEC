import Link from "next/link";
import { CapabilityStatusBadge } from "@/components/design-system/capability-status-badge";
import { PageHeader } from "@/components/design-system/page-header";

// GOVERNANCE landing (CDD-033 §23): presents only existing design-time
// governance -- Gate M's ontology proposal governance (already relocated
// to /ontology/modeling) -- as a link, not a duplicate embed of its
// stateful workspace. "Approvals" (Gate S) does not appear: the note below
// is descriptive only, never an interactive action. "Policies" links only
// to the existing, narrowly-scoped Entity Resolution policy-preview
// capability, never a generalized policy engine.
export default function Page() {
  return (
    <div className="max-w-5xl">
      <PageHeader eyebrow="Governance" title="Governance" />

      <section className="panel">
        <span className="eyebrow">Governance</span>
        <h2>Ontology Proposal Governance</h2>
        <p style={{ color: "var(--muted)" }}>
          Review, approve, reject, and publish proposed ontology concepts and
          relationships. This is CTEC&apos;s existing design-time governance
          capability, not a runtime human-approval workflow.
        </p>
        <div style={{ marginTop: "0.5rem" }}>
          <CapabilityStatusBadge status="SUPPORTED_NOW" />
        </div>
        <div style={{ marginTop: "0.75rem" }}>
          <Link className="button" href="/ontology/modeling">
            Open Ontology Proposal Governance
          </Link>
        </div>
      </section>

      <section className="panel" style={{ marginTop: "1.5rem" }}>
        <span className="eyebrow">Policies</span>
        <h2>Entity Resolution Policy Preview</h2>
        <p style={{ color: "var(--muted)" }}>
          Preview how a candidate resolution policy would decide an in-progress
          case. This is a narrowly-scoped, existing capability, not a
          generalized enterprise policy engine.
        </p>
        <div style={{ marginTop: "0.5rem" }}>
          <CapabilityStatusBadge status="SUPPORTED_NOW" />
        </div>
        <div style={{ marginTop: "0.75rem" }}>
          <Link className="button" href="/data/entity-resolution">
            Open Entity Resolution
          </Link>
        </div>
      </section>

      <section className="panel" style={{ marginTop: "1.5rem" }}>
        <span className="eyebrow">Approvals</span>
        <h2>Runtime human approval is not available</h2>
        <p style={{ color: "var(--muted)" }}>
          CTEC does not have a durable, cross-workspace human-approval workflow
          or approval queue for supply-chain decisions. Only the design-time
          ontology-proposal review above exists today.
        </p>
      </section>
    </div>
  );
}
