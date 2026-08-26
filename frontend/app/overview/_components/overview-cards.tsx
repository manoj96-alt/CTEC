"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState } from "@/components/design-system/empty-state";
import { entityResolutionApi } from "@/lib/entity-resolution/api-client";
import { ontologyModelingApi } from "@/lib/ontology-modeling/api-client";
import { ontologyApi } from "@/lib/ontology-studio/api-client";
import { supplierRiskApi } from "@/lib/supplier-risk/api-client";

// Real-data-only (CDD-033 §11, X-D3). Every count below comes from an
// already-authorized existing API call. A capability with no live
// aggregate API (Evidence Fitness, Simulation, generalized DQ) is simply
// absent from this list -- never represented by a fabricated number. Any
// call that fails or is unauthorized shows a truthful "Unavailable" state,
// never a fallback count of 0.
interface OverviewCard {
  label: string;
  href: string;
  count: number | null;
  unavailable: boolean;
}

export function OverviewCards() {
  const [cards, setCards] = useState<OverviewCard[] | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    Promise.allSettled([
      supplierRiskApi.queue(undefined, controller.signal),
      entityResolutionApi.queue(undefined, controller.signal),
      ontologyModelingApi.listProposals(undefined, controller.signal),
      ontologyApi.getConnectors(),
    ]).then(([supplierRisk, entityResolution, proposals, connectors]) => {
      setCards([
        {
          label: "Supplier risk assessments",
          href: "/intelligence/supplier-risk",
          count:
            supplierRisk.status === "fulfilled"
              ? supplierRisk.value.items.length
              : null,
          unavailable: supplierRisk.status === "rejected",
        },
        {
          label: "Entity resolution cases",
          href: "/data/entity-resolution",
          count:
            entityResolution.status === "fulfilled"
              ? entityResolution.value.items.length
              : null,
          unavailable: entityResolution.status === "rejected",
        },
        {
          label: "Ontology proposals",
          href: "/ontology/modeling",
          count:
            proposals.status === "fulfilled"
              ? proposals.value.proposals.length
              : null,
          unavailable: proposals.status === "rejected",
        },
        {
          label: "Connector catalog",
          href: "/integrations",
          count:
            connectors.status === "fulfilled"
              ? connectors.value.connectors.length
              : null,
          unavailable: connectors.status === "rejected",
        },
      ]);
    });
    return () => controller.abort();
  }, []);

  if (!cards) return <EmptyState kind="loading" title="Loading overview" />;

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(14rem, 1fr))",
        gap: "1rem",
      }}
    >
      {cards.map((card) => (
        <section key={card.label} className="panel">
          <span className="eyebrow">Overview</span>
          <h2>{card.label}</h2>
          {card.unavailable ? (
            <p style={{ color: "var(--muted)" }}>Unavailable</p>
          ) : (
            <p style={{ fontSize: "2rem", fontWeight: 700 }}>{card.count}</p>
          )}
          <Link className="button" href={card.href}>
            Open
          </Link>
        </section>
      ))}
      <section className="panel">
        <span className="eyebrow">Overview</span>
        <h2>Ask CTEC</h2>
        <p style={{ color: "var(--muted)" }}>
          Ask a governed question about the ontology.
        </p>
        <Link className="button" href="/intelligence/ask-ctec">
          Open
        </Link>
      </section>
    </div>
  );
}
