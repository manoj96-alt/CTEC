"use client";

import { useCallback, useMemo, useState } from "react";
import { loadDemoDataset } from "@/lib/demo/fixture-loader";
import { resolveScenarioFacts } from "@/lib/demo/scenario-facts";
import { buildOntologyModel } from "@/lib/demo/ontology-model";
import { evaluateDecision } from "@/lib/demo/decision-rules";
import type { DemoDataset } from "@/lib/demo/types";
import { StepIndicator } from "./step-indicator";
import { ImportDataStage } from "./import-data-stage";
import { SchemaMappingStage } from "./schema-mapping-stage";
import { OntologyExplorerStage } from "./ontology-explorer-stage";
import { DecisionFlowStage } from "./decision-flow-stage";
import { RecommendationStage } from "./recommendation-stage";
import { DecisionHistory, type DecisionHistoryEntry } from "./decision-history";
import { IncompleteEvidenceNotice } from "./incomplete-evidence-notice";

const DEMO_USER = "Demo Reviewer";

export function DemoScenarioController() {
  const [currentStep, setCurrentStep] = useState(1);
  const [highestCompletedStep, setHighestCompletedStep] = useState(0);
  const [dataset, setDataset] = useState<DemoDataset | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<DecisionHistoryEntry[]>([]);
  const [hasDecided, setHasDecided] = useState(false);

  const handleLoadSampleDataset = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const loaded = await loadDemoDataset();
      setDataset(loaded);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not load the sample dataset.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const advanceTo = useCallback((step: number) => {
    setCurrentStep(step);
    setHighestCompletedStep((prev) => Math.max(prev, step - 1));
  }, []);

  const scenarioResolution = useMemo(
    () => (dataset ? resolveScenarioFacts(dataset) : null),
    [dataset],
  );

  const ontologyModel = useMemo(
    () =>
      scenarioResolution?.complete
        ? buildOntologyModel(scenarioResolution)
        : null,
    [scenarioResolution],
  );

  const decisionEvaluation = useMemo(
    () =>
      scenarioResolution?.complete
        ? evaluateDecision(scenarioResolution)
        : null,
    [scenarioResolution],
  );

  const handleDecision = useCallback(
    (decision: "Approved" | "Rejected", comment: string) => {
      if (!decisionEvaluation?.recommendation) return;
      if (hasDecided) return; // BUG-001 fix: ignore rapid duplicate clicks
      setHasDecided(true);
      const entry: DecisionHistoryEntry = {
        id: `${Date.now()}`,
        decision,
        user: DEMO_USER,
        timestamp: new Date().toLocaleString(),
        recommendationSummary: decisionEvaluation.recommendation.summary,
        allocationPct: decisionEvaluation.recommendation.proposedAllocationPct,
        comment,
        evidenceReference: `${decisionEvaluation.conditions.length} source facts, ${decisionEvaluation.conditions.reduce((sum, c) => sum + c.sourceRefs.length, 0)} source rows`,
      };
      setHistory((prev) => [entry, ...prev]);
    },
    [decisionEvaluation, hasDecided],
  );

  const handleReset = useCallback(() => {
    setCurrentStep(1);
    setHighestCompletedStep(0);
    setDataset(null);
    setHasDecided(false);
    setError(null);
    setHistory([]);
  }, []);

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <div>
          <p className="eyebrow">Guided demo · Sample data</p>
          <h1 style={{ marginTop: "0.25rem" }}>Supplier Risk Walkthrough</h1>
        </div>
        <button type="button" className="secondary" onClick={handleReset}>
          Reset Demo
        </button>
      </div>

      <StepIndicator
        currentStep={currentStep}
        highestCompletedStep={highestCompletedStep}
        onStepSelect={setCurrentStep}
      />

      {currentStep === 1 && (
        <ImportDataStage
          dataset={dataset}
          loading={loading}
          error={error}
          onLoadSampleDataset={handleLoadSampleDataset}
          onContinue={() => advanceTo(2)}
        />
      )}

      {currentStep === 2 && (
        <SchemaMappingStage onBuildOntology={() => advanceTo(3)} />
      )}

      {currentStep === 3 &&
        scenarioResolution &&
        (scenarioResolution.complete && ontologyModel ? (
          <OntologyExplorerStage
            model={ontologyModel}
            onContinue={() => advanceTo(4)}
          />
        ) : !scenarioResolution.complete ? (
          <IncompleteEvidenceNotice
            resolution={scenarioResolution}
            stageLabel="Explore Ontology"
          />
        ) : null)}

      {currentStep === 4 &&
        scenarioResolution &&
        (scenarioResolution.complete && decisionEvaluation ? (
          <DecisionFlowStage
            evaluation={decisionEvaluation}
            onContinue={() => advanceTo(5)}
          />
        ) : !scenarioResolution.complete ? (
          <IncompleteEvidenceNotice
            resolution={scenarioResolution}
            stageLabel="Review Decision Flow"
          />
        ) : null)}

      {currentStep === 5 &&
        scenarioResolution &&
        (scenarioResolution.complete && decisionEvaluation ? (
          <>
            <RecommendationStage
              evaluation={decisionEvaluation}
              onDecision={handleDecision}
              hasDecided={hasDecided}
            />
            <DecisionHistory entries={history} />
          </>
        ) : !scenarioResolution.complete ? (
          <IncompleteEvidenceNotice
            resolution={scenarioResolution}
            stageLabel="Recommendation"
          />
        ) : null)}
    </div>
  );
}
