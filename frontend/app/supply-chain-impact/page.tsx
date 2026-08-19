"use client";

import { useState } from "react";
import { signIn } from "@/lib/auth/browser-session";
import {
  SupplyChainImpactApiError,
  supplyChainImpactApi,
} from "@/lib/supply-chain-impact/api-client";
import type { SupplyChainImpactEvaluateResponse } from "@/lib/supply-chain-impact/contracts";
import { AlternativesPanel } from "./_components/alternatives-panel";
import { BusinessImpactPanel } from "./_components/business-impact-panel";
import { EvidencePanel } from "./_components/evidence-panel";
import { HumanAuthorityBanner } from "./_components/human-authority-banner";
import { RecommendationPanel } from "./_components/recommendation-panel";
import { RiskSignalPanel } from "./_components/risk-signal-panel";

// The three deterministic Gate F demo scenarios (backend/app/infrastructure/
// persistence/demo_gate_f_seeder.py) -- known, fixed entry points, not a
// generic "list suppliers" capability (CDD-016 §6, presentation
// limitation #2). Seeded via `python -m app.infrastructure.persistence.
// demo_gate_f_seeder` against the labeled demo tenant.
const DEMO_SCENARIOS = [
  {
    key: "recommended",
    label: "High-risk supplier, qualified alternative",
    description: "Single-sourced, high-severity disruption, revenue exposure above the materiality threshold, one qualified and capable alternate supplier.",
    supplierEntityId: "5d98f421-ef60-5463-9c4e-f81b8bc63da1",
  },
  {
    key: "unknown",
    label: "Missing governed evidence",
    description: "Required disruption-severity evidence is genuinely unavailable. CTEC does not guess.",
    supplierEntityId: "8b2833c6-e347-5b98-925d-bbb0a8a71e12",
  },
  {
    key: "rejected",
    label: "Below the materiality threshold",
    description: "Revenue exposure is asserted but does not exceed the governed $10,000,000 threshold.",
    supplierEntityId: "dbd7299c-04a4-57b1-a506-43e4d3a172ff",
  },
] as const;

type WorkspaceState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "unauthenticated" }
  | { status: "forbidden" }
  | { status: "unavailable"; message: string }
  | { status: "result"; response: SupplyChainImpactEvaluateResponse };

export default function SupplyChainImpactPage() {
  const [state, setState] = useState<WorkspaceState>({ status: "idle" });

  async function runScenario(supplierEntityId: string) {
    setState({ status: "loading" });
    try {
      const response = await supplyChainImpactApi.evaluate(supplierEntityId);
      setState({ status: "result", response });
    } catch (error) {
      if (error instanceof SupplyChainImpactApiError) {
        if (error.status === 401) {
          setState({ status: "unauthenticated" });
          return;
        }
        if (error.status === 403) {
          setState({ status: "forbidden" });
          return;
        }
        setState({ status: "unavailable", message: error.code });
        return;
      }
      setState({ status: "unavailable", message: "SERVICE_UNAVAILABLE" });
    }
  }

  const result = state.status === "result" ? state.response : null;
  const material = result?.materials[0];
  const candidate = material?.candidates[0];

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">Supply chain impact</span>
          <h1>Governed supplier risk</h1>
          <p>
            A deterministic, governed walkthrough of the Gate F supply-chain impact and
            mitigation capability. Every fact and conclusion below comes from the
            authenticated Gate F API -- no business decision is made in this browser.
          </p>
        </div>
      </div>

      <section className="panel" aria-label="Scenario selection">
        <div className="eyebrow">Choose a governed scenario</div>
        <div className="action-row" style={{ flexWrap: "wrap" }}>
          {DEMO_SCENARIOS.map((scenario) => (
            <button
              key={scenario.key}
              className="button"
              type="button"
              disabled={state.status === "loading"}
              onClick={() => void runScenario(scenario.supplierEntityId)}
            >
              {scenario.label}
            </button>
          ))}
        </div>
        <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
          {DEMO_SCENARIOS.map((scenario) => (
            <span key={scenario.key} style={{ display: "block" }}>
              <strong>{scenario.label}:</strong> {scenario.description}
            </span>
          ))}
        </p>
      </section>

      {state.status === "loading" && (
        <section className="panel" role="status">
          <h2>Evaluating</h2>
          <p>Retrieving governed impact and mitigation state…</p>
        </section>
      )}

      {state.status === "unauthenticated" && (
        <section className="panel" role="status">
          <h2>Sign-in required</h2>
          <p>You must sign in before Gate F can evaluate this scenario.</p>
          <button
            className="button"
            type="button"
            onClick={() => void signIn("/supply-chain-impact")}
          >
            Sign in
          </button>
        </section>
      )}

      {state.status === "forbidden" && (
        <section className="panel" role="status">
          <h2>Additional authority required</h2>
          <p>
            Your account does not hold the <code>supply-chain-impact:evaluate</code> scope
            required to initiate a governed evaluation. You may still be able to view a
            previously-created evaluation if you hold <code>supply-chain-impact:read</code>.
          </p>
        </section>
      )}

      {state.status === "unavailable" && (
        <section className="panel" role="status">
          <h2>Gate F is unavailable</h2>
          <p>The governed backend could not complete this request ({state.message}).</p>
        </section>
      )}

      {result && (
        <>
          <RiskSignalPanel
            supplierName={result.impact.supplier_name}
            material={material}
            evidence={candidate?.evidence ?? []}
          />
          <BusinessImpactPanel
            impact={result.impact}
            singleSourceExposure={material?.single_source_exposure ?? null}
            revenueMateriality={material?.revenue_materiality ?? null}
            evidence={candidate?.evidence ?? []}
          />
          <EvidencePanel evidence={candidate?.evidence ?? []} />
          <AlternativesPanel candidates={material?.candidates ?? []} />
          <RecommendationPanel
            candidate={candidate}
            policyReference={result.policy_reference}
            policyVersion={result.policy_version}
          />
          <HumanAuthorityBanner governanceStanding={result.governance_standing} />
        </>
      )}
    </div>
  );
}
