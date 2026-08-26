"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ConnectorCatalogPanel } from "@/app/ontology-studio/_components/connector-catalog-panel";
import { PageHeader } from "@/components/design-system/page-header";
import {
  ontologyApi,
  OntologyApiError,
} from "@/lib/ontology-studio/api-client";
import type { Connector } from "@/lib/ontology-studio/contracts";

// DATA domain landing (CDD-033 §12): Sources relocates the existing static
// connector-catalog presentation (reuses `ConnectorCatalogPanel` and
// `ontologyApi.getConnectors()` verbatim, same pattern as Integrations).
// Entity Resolution relocates the existing live workspace unchanged. No
// dataset/data-product/ingestion/DQ metric is invented -- "Ingestion" is
// FUTURE GATE and absent from v1 navigation.
export default function Page() {
  const [connectors, setConnectors] = useState<Connector[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    ontologyApi
      .getConnectors()
      .then((response) => setConnectors(response.connectors))
      .catch((e) => {
        setError(e instanceof OntologyApiError ? e.message : String(e));
      });
  }, []);

  return (
    <div className="max-w-5xl">
      <PageHeader eyebrow="Data" title="Data" />

      <section className="panel">
        <span className="eyebrow">Data</span>
        <h2>Entity Resolution</h2>
        <p style={{ color: "var(--muted)" }}>
          Review multi-attribute evidence and record resolution decisions for
          supplier candidates.
        </p>
        <div style={{ marginTop: "0.75rem" }}>
          <Link className="button" href="/data/entity-resolution">
            Open Entity Resolution
          </Link>
        </div>
      </section>

      <div style={{ marginTop: "1.5rem" }}>
        <span className="eyebrow">Data</span>
        <h2>Sources</h2>
        {error ? (
          <section className="panel" role="alert">
            <h2>Connector catalog unavailable</h2>
            <p>{error}</p>
          </section>
        ) : connectors ? (
          <ConnectorCatalogPanel connectors={connectors} />
        ) : (
          <p>Loading…</p>
        )}
      </div>
    </div>
  );
}
