"use client";

import { useEffect, useState } from "react";
import {
  ontologyApi,
  OntologyApiError,
} from "@/lib/ontology-studio/api-client";
import type {
  Connector,
  OntologyDetail,
} from "@/lib/ontology-studio/contracts";
import { StudioOverview, connectorCount } from "./studio-overview";
import { ConnectorCatalogPanel } from "./connector-catalog-panel";
import { OntologyGraph } from "./ontology-graph";
import { QualityPanel } from "./quality-panel";
import { ApiExportPanel } from "./api-export-panel";
import { ActivationCard } from "./activation-card";
import { EntityResolutionLinkCard } from "./entity-resolution-link-card";
import { AskCtecLinkCard } from "./ask-ctec-link-card";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "ready";
      ontology: OntologyDetail;
      connectors: Connector[];
      exportPreview: Record<string, unknown> | null;
    };

async function loadStudioData(): Promise<LoadState> {
  try {
    const [ontology, connectorsResponse] = await Promise.all([
      ontologyApi.getOntology("supplier-risk"),
      ontologyApi.getConnectors(),
    ]);
    let exportPreview: Record<string, unknown> | null = null;
    try {
      exportPreview = await ontologyApi.getExportPreview("supplier-risk");
    } catch {
      exportPreview = null;
    }
    return {
      status: "ready",
      ontology,
      connectors: connectorsResponse.connectors,
      exportPreview,
    };
  } catch (error) {
    const message =
      error instanceof OntologyApiError
        ? error.message
        : "The ontology service could not be reached.";
    return { status: "error", message };
  }
}

export function StudioClient() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  const retry = () => {
    setState({ status: "loading" });
    loadStudioData().then(setState);
  };

  useEffect(() => {
    loadStudioData().then(setState);
  }, []);

  if (state.status === "loading") {
    return (
      <div className="panel" role="status">
        Loading ontology from the published Ontology Service…
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="panel" role="alert">
        <p style={{ fontWeight: 700 }}>Ontology service unavailable</p>
        <p style={{ color: "var(--muted)" }}>{state.message}</p>
        <button
          type="button"
          className="button"
          style={{ marginTop: "0.75rem" }}
          onClick={retry}
        >
          Retry
        </button>
      </div>
    );
  }

  const { ontology, connectors, exportPreview } = state;

  if (ontology.concepts.length === 0) {
    return (
      <div className="panel">
        <p style={{ fontWeight: 700 }}>No ontology data is available yet</p>
        <p style={{ color: "var(--muted)" }}>
          The ontology has not been seeded. No concepts or relationships are
          currently published.
        </p>
      </div>
    );
  }

  return (
    <div>
      <StudioOverview
        ontology={ontology}
        connectorCount={connectorCount(connectors)}
      />
      <EntityResolutionLinkCard />
      <AskCtecLinkCard />
      <ConnectorCatalogPanel connectors={connectors} />
      <OntologyGraph
        concepts={ontology.concepts}
        relationships={ontology.relationships}
      />
      <QualityPanel quality={ontology.quality} />
      <ApiExportPanel preview={exportPreview} />
      <ActivationCard version={ontology.version} />
    </div>
  );
}
