"use client";

import { useCallback, useEffect, useState } from "react";
import { ontologyApi } from "@/lib/ontology-studio/api-client";
import type { Concept } from "@/lib/ontology-studio/contracts";
import {
  OntologyModelingApiError,
  ontologyModelingApi,
} from "@/lib/ontology-modeling/api-client";
import type { ProposalDetail } from "@/lib/ontology-modeling/contracts";
import { ProposeForm } from "./propose-form";
import { ProposalList } from "./proposal-list";

type ConceptsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; concepts: Concept[] };

type ProposalsState =
  | { status: "loading" }
  | { status: "unauthorized" }
  | { status: "error"; message: string }
  | { status: "ready"; proposals: ProposalDetail[] };

export function OntologyModelingWorkspace() {
  // VIEW: the existing, unmodified, read-only ontology surface -- reused
  // by call only, never modified. Populates the Relationship-proposal
  // source/target dropdowns and gives visual context for MODEL.
  const [conceptsState, setConceptsState] = useState<ConceptsState>({
    status: "loading",
  });
  const [proposalsState, setProposalsState] = useState<ProposalsState>({
    status: "loading",
  });
  const [refreshToken, setRefreshToken] = useState(0);

  const refresh = useCallback(() => {
    setProposalsState({ status: "loading" });
    setRefreshToken((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    ontologyApi
      .getOntology("supplier-risk")
      .then((detail) => {
        setConceptsState({ status: "ready", concepts: detail.concepts });
      })
      .catch(() => {
        setConceptsState({
          status: "error",
          message: "The governed ontology could not be loaded.",
        });
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    ontologyModelingApi
      .listProposals(undefined, controller.signal)
      .then((result) => {
        setProposalsState({ status: "ready", proposals: result.proposals });
      })
      .catch((error: unknown) => {
        if (error instanceof Error && error.name === "AbortError") return;
        if (
          error instanceof OntologyModelingApiError &&
          (error.code === "AUTH_REQUIRED" || error.status === 401)
        ) {
          setProposalsState({ status: "unauthorized" });
          return;
        }
        if (error instanceof OntologyModelingApiError && error.status === 403) {
          setProposalsState({
            status: "error",
            message:
              "You are not authorized to view ontology modeling proposals.",
          });
          return;
        }
        setProposalsState({
          status: "error",
          message: "The Ontology Modeling service could not be reached.",
        });
      });
    return () => controller.abort();
  }, [refreshToken]);

  return (
    <section>
      <p className="eyebrow">Ontology Studio</p>
      <h1 style={{ marginTop: "0.25rem" }}>
        Governed Visual Ontology Modeling
      </h1>
      <p style={{ color: "var(--muted)" }}>
        Propose a net-new Concept or Relationship. A proposal never mutates the
        governed ontology -- only a separately authorized Publish action,
        applied to an Approved proposal, creates a new canonical object.
        Modifying an existing Concept or Relationship is not yet supported.
      </p>

      {conceptsState.status === "loading" && (
        <p>Loading the governed ontology…</p>
      )}
      {conceptsState.status === "error" && (
        <div className="error-summary" role="alert">
          {conceptsState.message}
        </div>
      )}
      {conceptsState.status === "ready" && (
        <ProposeForm concepts={conceptsState.concepts} onProposed={refresh} />
      )}

      {proposalsState.status === "loading" && <p>Loading proposals…</p>}
      {proposalsState.status === "unauthorized" && (
        <div className="error-summary" role="alert">
          Sign in is required to view ontology modeling proposals.
        </div>
      )}
      {proposalsState.status === "error" && (
        <div className="error-summary" role="alert">
          {proposalsState.message}
        </div>
      )}
      {proposalsState.status === "ready" && (
        <ProposalList
          proposals={proposalsState.proposals}
          onChanged={refresh}
        />
      )}
    </section>
  );
}
