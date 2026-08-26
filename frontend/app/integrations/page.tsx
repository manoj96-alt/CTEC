"use client";

import { useEffect, useState } from "react";
import { ConnectorCatalogPanel } from "@/app/ontology-studio/_components/connector-catalog-panel";
import { PageHeader } from "@/components/design-system/page-header";
import {
  ontologyApi,
  OntologyApiError,
} from "@/lib/ontology-studio/api-client";
import type { Connector } from "@/lib/ontology-studio/contracts";

// INTEGRATIONS landing (CDD-033 §22): the existing static ontology
// connector catalog, relocated with zero logic change (reuses
// `ConnectorCatalogPanel` and `ontologyApi.getConnectors()` verbatim). MCP
// (Gate Q) has zero API/UI by CDD-030's own design and appears only as a
// descriptive, non-interactive mention -- never an execution surface.
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
      <PageHeader eyebrow="Integrations" title="Integrations" />

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

      <section className="panel" style={{ marginTop: "1.5rem" }}>
        <span className="eyebrow">Model Context Protocol</span>
        <h2>MCP</h2>
        <p style={{ color: "var(--muted)" }}>
          CTEC can discover MCP tool capabilities as a governed backend concept.
          Discovery is not execution: there is no interactive way to connect,
          invoke, or run an MCP tool from this workspace.
        </p>
      </section>
    </div>
  );
}
