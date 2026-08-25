import { CapabilityStatusBadge } from "@/components/design-system/capability-status-badge";
import { PageHeader } from "@/components/design-system/page-header";

// Standalone What-if Simulation presentation (CDD-033 §21, X-D1). Gate X
// does not authorize any API for Gate U -- this page is capability/status/
// documentation only. There is deliberately no form, no "Run Simulation" /
// "Execute" / "Calculate Impact" action, and no example result of any kind:
// a fabricated number here would violate CDD-033 §21/§37 exactly as
// fabricating a live Evidence Fitness record would violate §17.
export default function Page() {
  return (
    <div className="max-w-5xl">
      <PageHeader
        eyebrow="Intelligence"
        title="Simulation"
        description="Gate U's governed what-if simulation capability, presented here as capability and status information only."
        action={<CapabilityStatusBadge status="AVAILABLE_BUT_DISCONNECTED" />}
      />

      <section className="panel">
        <span className="eyebrow">Status</span>
        <h2>Simulation is not executable in this workspace</h2>
        <p style={{ color: "var(--muted)" }}>
          CTEC can compute a hypothetical, ephemeral evidence-fitness impact for
          a proposed information-element state as a governed backend capability.
          That capability is not exposed through any authorized Gate X frontend
          contract in this release, so this page cannot accept an input, run a
          scenario, or display a result for any supplier or information element.
        </p>
      </section>

      <section className="panel" style={{ marginTop: "1.5rem" }}>
        <span className="eyebrow">Governed boundary</span>
        <h2>Simulation semantics</h2>
        <p style={{ color: "var(--muted)" }}>
          When exposed, every simulation result will be, without exception:
        </p>
        <ul style={{ marginTop: "0.5rem", color: "var(--muted)" }}>
          <li>
            <strong>SIMULATION</strong> — a what-if computation, not a governed
            evaluation
          </li>
          <li>
            <strong>HYPOTHETICAL</strong> — based on a proposed, not actual,
            state
          </li>
          <li>
            <strong>NON-AUTHORITATIVE</strong> — never a substitute for a real
            Gate T or Gate F result
          </li>
          <li>
            <strong>NO PERSISTENCE</strong> — never saved as a durable record
          </li>
          <li>
            <strong>NO EXECUTION</strong> — never triggers a real action or
            decision
          </li>
        </ul>
      </section>

      <section className="panel" style={{ marginTop: "1.5rem" }}>
        <span className="eyebrow">Related, not connected</span>
        <h2>Supplier Risk</h2>
        <p style={{ color: "var(--muted)" }}>
          Simulation is a distinct, already-governed capability (CDD-032) and is
          not part of, and does not imply, a runtime bridge with Supplier
          Risk&apos;s decision pipeline.
        </p>
      </section>
    </div>
  );
}
