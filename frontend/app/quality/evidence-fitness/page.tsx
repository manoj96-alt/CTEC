"use client";

import { useState } from "react";
import Link from "next/link";
import { EmptyState } from "@/components/design-system/empty-state";
import { PageHeader } from "@/components/design-system/page-header";
import {
  EvidenceFitnessApiError,
  evidenceFitnessApi,
} from "@/lib/evidence-fitness/api-client";
import type { ResolveResponse } from "@/lib/evidence-fitness/contracts";

// CDD-034 Evidence Fitness Frontend Exposure Authorization sec8: exactly
// nine governed states. The frontend consumes and renders the backend's
// response only -- it never computes, infers, or approximates a
// fitness/staleness/conflict determination (sec6). "UNMAPPED"
// (source_field_id: null) and "mapped, no evaluable evidence"
// (fitness_status: null with a real source_field_id) are deliberately
// distinct states and are never conflated (sec8, sec11 of the parent
// CDD-034).
type CheckState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "result"; result: ResolveResponse }
  | { status: "unauthorized" }
  | { status: "not_found"; code: string }
  | { status: "validation_error"; code: string }
  | { status: "error"; code: string };

function describeFailure(code: string): string {
  switch (code) {
    case "BLUEPRINT_NOT_FOUND":
      return "No governed blueprint matches that name.";
    case "INFORMATION_ELEMENT_NOT_FOUND":
      return "No information element with that name exists on the resolved blueprint.";
    case "INFORMATION_ELEMENT_NAME_AMBIGUOUS":
      return "That information element name matches more than one requirement on the blueprint; use a more specific name.";
    default:
      return `Request failed (${code}).`;
  }
}

export default function Page() {
  const [blueprintName, setBlueprintName] = useState("");
  const [informationElementName, setInformationElementName] = useState("");
  const [state, setState] = useState<CheckState>({ status: "idle" });

  const canSubmit =
    blueprintName.trim().length > 0 && informationElementName.trim().length > 0;

  async function submit() {
    setState({ status: "loading" });
    try {
      const result = await evidenceFitnessApi.resolve({
        blueprint_name: blueprintName,
        information_element_name: informationElementName,
      });
      setState({ status: "result", result });
    } catch (caught) {
      if (caught instanceof EvidenceFitnessApiError) {
        if (caught.status === 401 || caught.status === 403) {
          setState({ status: "unauthorized" });
          return;
        }
        if (caught.status === 404) {
          setState({ status: "not_found", code: caught.code });
          return;
        }
        if (caught.status === 422) {
          setState({ status: "validation_error", code: caught.code });
          return;
        }
        setState({ status: "error", code: caught.code });
        return;
      }
      setState({ status: "error", code: "UNKNOWN_ERROR" });
    }
  }

  return (
    <div className="max-w-5xl">
      <PageHeader
        eyebrow="Quality"
        title="Evidence Fitness"
        description="Check whether a specific Information Element's evidence is fit, stale, or conflicting -- Gate T's governed evidence-fitness evaluation (CDD-031), exposed read-only through CDD-034's resolve endpoint."
      />

      <section className="panel">
        <span className="eyebrow">Check evidence fitness</span>
        <h2>Resolve evidence fitness</h2>
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
            {state.status === "loading"
              ? "Checking…"
              : "Check Evidence Fitness"}
          </button>
        </div>
      </section>

      {state.status === "loading" && (
        <EmptyState kind="loading" title="Checking evidence fitness" />
      )}

      {state.status === "unauthorized" && (
        <EmptyState
          kind="error"
          title="Not authorized"
          message="You are not authorized to check evidence fitness."
        />
      )}

      {state.status === "not_found" && (
        <EmptyState
          kind="error"
          title="Not found"
          message={describeFailure(state.code)}
        />
      )}

      {state.status === "validation_error" && (
        <EmptyState
          kind="error"
          title="Request could not be resolved"
          message={describeFailure(state.code)}
        />
      )}

      {state.status === "error" && (
        <EmptyState
          kind="error"
          title="Evidence Fitness could not be checked"
          message={describeFailure(state.code)}
        />
      )}

      {state.status === "result" && (
        <section className="panel" style={{ marginTop: "1rem" }}>
          <span className="eyebrow">Governed result</span>
          {state.result.source_field_id === null ? (
            <>
              <h2>Not mapped</h2>
              <p style={{ color: "var(--muted)" }}>
                No source field is mapped to this information element -- there
                is no evidence to evaluate.
              </p>
            </>
          ) : state.result.fitness_status === null ? (
            <>
              <h2>Mapped, no evaluable evidence</h2>
              <p style={{ color: "var(--muted)" }}>
                A source field is mapped to this information element, but no
                evaluable evidence exists for it yet.
              </p>
            </>
          ) : (
            <>
              <h2>{state.result.fitness_status}</h2>
              <p style={{ color: "var(--muted)" }}>
                {state.result.fitness_status === "FIT" &&
                  "The available evidence satisfies the information element's requirement."}
                {state.result.fitness_status === "STALE" &&
                  "The available evidence is out of date and requires refresh."}
                {state.result.fitness_status === "CONFLICTING" &&
                  "Multiple sources disagree and require review."}
              </p>
            </>
          )}
          <p style={{ color: "var(--muted)", marginTop: "0.5rem" }}>
            Evaluated at {state.result.evaluated_at}
          </p>
        </section>
      )}

      <section className="panel" style={{ marginTop: "1.5rem" }}>
        <span className="eyebrow">Governed vocabulary</span>
        <h2>Fitness statuses</h2>
        <p style={{ color: "var(--muted)" }}>
          Each information element&apos;s evidence is classified into one of
          three governed statuses:
        </p>
        <dl style={{ marginTop: "0.75rem" }}>
          <dt style={{ fontWeight: 700 }}>FIT</dt>
          <dd style={{ color: "var(--muted)" }}>
            The available evidence satisfies the information element&apos;s
            requirement.
          </dd>
          <dt style={{ fontWeight: 700, marginTop: "0.5rem" }}>STALE</dt>
          <dd style={{ color: "var(--muted)" }}>
            The available evidence is out of date and requires refresh.
          </dd>
          <dt style={{ fontWeight: 700, marginTop: "0.5rem" }}>CONFLICTING</dt>
          <dd style={{ color: "var(--muted)" }}>
            Multiple sources disagree and require review.
          </dd>
        </dl>
      </section>

      <section className="panel" style={{ marginTop: "1.5rem" }}>
        <span className="eyebrow">Related, not connected</span>
        <h2>Generalized Data Quality</h2>
        <p style={{ color: "var(--muted)" }}>
          Evidence Fitness is a distinct, already-governed capability (CDD-031)
          and is not part of, and does not imply, the separate generalized Data
          Quality capability marked Planned on the Quality landing page.
        </p>
      </section>

      <p style={{ marginTop: "1.5rem" }}>
        <Link href="/quality">Back to Quality</Link>
      </p>
    </div>
  );
}
