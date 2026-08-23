"use client";

import { useState } from "react";
import type { Concept } from "@/lib/ontology-studio/contracts";
import {
  OntologyModelingApiError,
  ontologyModelingApi,
} from "@/lib/ontology-modeling/api-client";

// MODEL, deliberately form-based, not canvas-editing (Gate M Artifact
// Authorization v1.1 §4.10): a plain form for a net-new Concept or
// Relationship. No graph-canvas editing, no drag-and-drop node creation, no
// ReactFlow integration -- ontology-graph.tsx is neither imported nor
// extended by this file. Client-side length checks here are UX sugar only;
// the backend re-validates authoritatively (AA v1.1 §4.1's __post_init__).
const MAX_NAME_LENGTH = 200;
const MAX_DEFINITION_LENGTH = 2000;

type Kind = "CreateConcept" | "CreateRelationship";

export function ProposeForm({
  concepts,
  onProposed,
}: {
  concepts: Concept[];
  onProposed: () => void;
}) {
  const [kind, setKind] = useState<Kind>("CreateConcept");
  const [entityTypeName, setEntityTypeName] = useState("");
  const [definition, setDefinition] = useState("");
  const [relationshipTypeName, setRelationshipTypeName] = useState("");
  const [sourceEntityTypeId, setSourceEntityTypeId] = useState("");
  const [targetEntityTypeId, setTargetEntityTypeId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function resetFields() {
    setEntityTypeName("");
    setDefinition("");
    setRelationshipTypeName("");
    setSourceEntityTypeId("");
    setTargetEntityTypeId("");
  }

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      if (kind === "CreateConcept") {
        await ontologyModelingApi.proposeConcept({
          proposal_kind: "CreateConcept",
          entity_type_name: entityTypeName,
          definition: definition || null,
        });
      } else {
        await ontologyModelingApi.proposeRelationship({
          proposal_kind: "CreateRelationship",
          relationship_type_name: relationshipTypeName,
          source_entity_type_id: sourceEntityTypeId,
          target_entity_type_id: targetEntityTypeId,
        });
      }
      resetFields();
      onProposed();
    } catch (caught) {
      if (caught instanceof OntologyModelingApiError) {
        setError(caught.code);
      } else {
        setError("The proposal could not be submitted.");
      }
    } finally {
      setBusy(false);
    }
  }

  const canSubmit =
    kind === "CreateConcept"
      ? entityTypeName.trim().length > 0 &&
        entityTypeName.length <= MAX_NAME_LENGTH &&
        definition.length <= MAX_DEFINITION_LENGTH
      : relationshipTypeName.trim().length > 0 &&
        relationshipTypeName.length <= MAX_NAME_LENGTH &&
        sourceEntityTypeId.length > 0 &&
        targetEntityTypeId.length > 0;

  return (
    <section className="panel" style={{ marginTop: "1rem" }}>
      <h2>Propose a net-new object</h2>
      <div style={{ display: "flex", gap: "1rem", marginTop: "0.5rem" }}>
        <label>
          <input
            type="radio"
            name="proposal-kind"
            checked={kind === "CreateConcept"}
            onChange={() => setKind("CreateConcept")}
          />{" "}
          New Concept
        </label>
        <label>
          <input
            type="radio"
            name="proposal-kind"
            checked={kind === "CreateRelationship"}
            onChange={() => setKind("CreateRelationship")}
          />{" "}
          New Relationship
        </label>
      </div>

      {kind === "CreateConcept" ? (
        <>
          <label style={{ display: "block", marginTop: "0.75rem" }}>
            Concept name
            <input
              type="text"
              value={entityTypeName}
              onChange={(e) => setEntityTypeName(e.target.value)}
              maxLength={MAX_NAME_LENGTH}
              required
            />
          </label>
          <label style={{ display: "block", marginTop: "0.5rem" }}>
            Definition (optional)
            <textarea
              value={definition}
              onChange={(e) => setDefinition(e.target.value)}
              maxLength={MAX_DEFINITION_LENGTH}
            />
          </label>
        </>
      ) : (
        <>
          <label style={{ display: "block", marginTop: "0.75rem" }}>
            Relationship name
            <input
              type="text"
              value={relationshipTypeName}
              onChange={(e) => setRelationshipTypeName(e.target.value)}
              maxLength={MAX_NAME_LENGTH}
              required
            />
          </label>
          <label style={{ display: "block", marginTop: "0.5rem" }}>
            Source concept
            <select
              value={sourceEntityTypeId}
              onChange={(e) => setSourceEntityTypeId(e.target.value)}
              required
            >
              <option value="">Select a source concept…</option>
              {concepts.map((c) => (
                <option key={c.entity_type_id} value={c.entity_type_id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <label style={{ display: "block", marginTop: "0.5rem" }}>
            Target concept
            <select
              value={targetEntityTypeId}
              onChange={(e) => setTargetEntityTypeId(e.target.value)}
              required
            >
              <option value="">Select a target concept…</option>
              {concepts.map((c) => (
                <option key={c.entity_type_id} value={c.entity_type_id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
        </>
      )}

      {error && (
        <div
          className="error-summary"
          role="alert"
          style={{ marginTop: "0.5rem" }}
        >
          {error}
        </div>
      )}

      <div style={{ marginTop: "0.75rem" }}>
        <button
          type="button"
          className="button"
          disabled={busy || !canSubmit}
          onClick={() => void submit()}
        >
          {busy ? "Submitting…" : "Submit proposal"}
        </button>
      </div>
    </section>
  );
}
