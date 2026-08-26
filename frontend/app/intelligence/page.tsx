import Link from "next/link";
import { CapabilityStatusBadge } from "@/components/design-system/capability-status-badge";
import { PageHeader } from "@/components/design-system/page-header";

// INTELLIGENCE domain landing (CDD-033 §19). Ask CTEC and Supplier Risk are
// existing, live, relocated workspaces; Decisions is a frontend-only
// aggregation of existing Gate F execution history; Simulation is a real
// backend capability (Gate U, CDD-032) with zero authorized frontend API,
// so it is classified AVAILABLE_BUT_DISCONNECTED here, matching Evidence
// Fitness's own classification for the identical situation (CDD-033 §15).
const CARDS = [
  {
    name: "Ask CTEC",
    href: "/intelligence/ask-ctec",
    status: "SUPPORTED_NOW" as const,
  },
  {
    name: "Decisions",
    href: "/intelligence/decisions",
    status: "SUPPORTED_NOW" as const,
  },
  {
    name: "Supplier Risk",
    href: "/intelligence/supplier-risk",
    status: "SUPPORTED_NOW" as const,
  },
  {
    name: "Simulation",
    href: "/simulation",
    status: "AVAILABLE_BUT_DISCONNECTED" as const,
  },
];

export default function Page() {
  return (
    <div className="max-w-5xl">
      <PageHeader eyebrow="Intelligence" title="Intelligence" />
      <div
        style={{
          marginTop: "1rem",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(14rem, 1fr))",
          gap: "1rem",
        }}
      >
        {CARDS.map((card) => (
          <section key={card.name} className="panel">
            <span className="eyebrow">Intelligence</span>
            <h2>{card.name}</h2>
            <div style={{ marginTop: "0.5rem" }}>
              <CapabilityStatusBadge status={card.status} />
            </div>
            <div style={{ marginTop: "0.75rem" }}>
              <Link className="button" href={card.href}>
                Open {card.name}
              </Link>
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
