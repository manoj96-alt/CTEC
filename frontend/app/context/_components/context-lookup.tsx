"use client";

import { useState } from "react";
import { signIn } from "@/lib/auth/browser-session";
import { EmptyState } from "@/components/design-system/empty-state";
import { ContextApiError, contextApi } from "@/lib/context/api-client";
import type { ResolveResponse } from "@/lib/context/contracts";
import { useContextIdentifiers } from "@/lib/context/context-provider";

// Manual/free-text identifier entry only (Gate X7 P2-3): the Gate O
// resolve contract accepts exactly `blueprint_name` and
// `information_element_name` -- there is no authorized blueprint or
// information-element listing endpoint to back a dropdown or autocomplete,
// so inventing one would exceed the Artifact Authorization's API-consumption
// boundary (§9).
type LookupState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "result"; result: ResolveResponse }
  | { status: "error"; code: string; httpStatus: number };

function describeError(code: string, httpStatus: number): string {
  switch (code) {
    case "BLUEPRINT_NOT_FOUND":
      return "No governed blueprint matches that name.";
    case "INFORMATION_ELEMENT_NOT_FOUND":
      return "No information element with that name exists on the resolved blueprint.";
    case "INFORMATION_ELEMENT_NAME_AMBIGUOUS":
      return "That information element name matches more than one requirement on the blueprint; use a more specific name.";
    case "AUTHORIZATION_SCOPE_REQUIRED":
      return "Your session is not authorized to read governed context.";
    case "UPSTREAM_INTEGRITY_FAILURE":
      return "A governed upstream dependency failed. Try again.";
    default:
      return httpStatus
        ? `Request failed (HTTP ${httpStatus}).`
        : "Request failed.";
  }
}

export function ContextLookup() {
  const [blueprintName, setBlueprintName] = useState("");
  const [informationElementName, setInformationElementName] = useState("");
  const [state, setState] = useState<LookupState>({ status: "idle" });
  const { setContextIdentifiers } = useContextIdentifiers();

  const canSubmit =
    blueprintName.trim().length > 0 && informationElementName.trim().length > 0;

  async function submit() {
    setState({ status: "loading" });
    try {
      const result = await contextApi.resolve({
        blueprint_name: blueprintName,
        information_element_name: informationElementName,
      });
      setContextIdentifiers({
        blueprintId: result.blueprint_id,
        informationElementRequirementId:
          result.information_element_requirement_id,
      });
      setState({ status: "result", result });
    } catch (caught) {
      if (caught instanceof ContextApiError) {
        if (caught.status === 401) {
          await signIn("/context");
          return;
        }
        setState({
          status: "error",
          code: caught.code,
          httpStatus: caught.status,
        });
        return;
      }
      setState({ status: "error", code: "UNKNOWN_ERROR", httpStatus: 0 });
    }
  }

  return (
    <div>
      <section className="panel">
        <span className="eyebrow">Look up governed context</span>
        <h2>Resolve blueprint context</h2>
        <label style={{ display: "block", marginTop: "0.75rem" }}>
          Blueprint name
          <input
            type="text"
            value={blueprintName}
            onChange={(e) => setBlueprintName(e.target.value)}
            required
          />
        </label>
        <label style={{ display: "block", marginTop: "0.5rem" }}>
          Information element name
          <input
            type="text"
            value={informationElementName}
            onChange={(e) => setInformationElementName(e.target.value)}
            required
          />
        </label>
        <div style={{ marginTop: "0.75rem" }}>
          <button
            type="button"
            className="button"
            disabled={state.status === "loading" || !canSubmit}
            onClick={() => void submit()}
          >
            {state.status === "loading" ? "Resolving…" : "Resolve context"}
          </button>
        </div>
      </section>

      {state.status === "loading" && (
        <EmptyState kind="loading" title="Resolving context" />
      )}

      {state.status === "error" && (
        <EmptyState
          kind="error"
          title="Context could not be resolved"
          message={describeError(state.code, state.httpStatus)}
        />
      )}

      {state.status === "result" && (
        <section className="panel" style={{ marginTop: "1rem" }}>
          <span className="eyebrow">Governed context</span>
          <h2>{state.result.information_element_name}</h2>
          <p style={{ color: "var(--muted)" }}>
            Blueprint version {state.result.blueprint_version_number}
          </p>
          <dl>
            <dt style={{ fontWeight: 700 }}>Obligation</dt>
            <dd>{state.result.obligation}</dd>
            <dt style={{ fontWeight: 700, marginTop: "0.5rem" }}>
              Coverage status
            </dt>
            <dd>{state.result.coverage_status}</dd>
            <dt style={{ fontWeight: 700, marginTop: "0.5rem" }}>
              Evidence availability
            </dt>
            <dd>
              {state.result.evidence_availability_status ?? "Not available"}
            </dd>
          </dl>
        </section>
      )}
    </div>
  );
}
