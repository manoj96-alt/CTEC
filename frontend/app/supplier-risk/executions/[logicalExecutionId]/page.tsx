"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AttemptHistory } from "@/components/supplier-risk/attempt-history";
import { RecommendationPanel } from "@/components/supplier-risk/recommendation-panel";
import { ReplayDialog } from "@/components/supplier-risk/replay-dialog";
import { RetryDialog } from "@/components/supplier-risk/retry-dialog";
import { RouteState } from "@/components/supplier-risk/route-state";
import { StageTimeline } from "@/components/supplier-risk/stage-timeline";
import { StatusSummary } from "@/components/supplier-risk/status-summary";
import { supplierRiskApi } from "@/lib/supplier-risk/api-client";
import { nextPollDelay, shouldPoll } from "@/lib/supplier-risk/polling";
import type {
  Attempt,
  GovernedResult,
  ReplayOption,
  RetryEligibility,
  Stage,
  TerminalClassification,
} from "@/lib/supplier-risk/contracts";
export default function ExecutionPage() {
  const params = useParams<{ logicalExecutionId: string }>();
  const id = params.logicalExecutionId;
  const [execution, setExecution] = useState<Record<string, unknown> | null>(
    null,
  );
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [stages, setStages] = useState<Stage[]>([]);
  const [result, setResult] = useState<GovernedResult | null>(null);
  const [retry, setRetry] = useState<RetryEligibility | null>(null);
  const [replay, setReplay] = useState<ReplayOption[]>([]);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    try {
      const current = await supplierRiskApi.execution(id);
      setExecution(current);
      const history = await supplierRiskApi.attempts(id);
      const values = history.items as unknown as Attempt[];
      setAttempts(values);
      const latest = values.at(-1);
      if (latest)
        setStages(
          (await supplierRiskApi.stages(id, latest.execution_identifier)).items,
        );
      try {
        setResult(await supplierRiskApi.result(id));
      } catch {}
      try {
        setRetry(await supplierRiskApi.retryEligibility(id));
      } catch {}
      try {
        setReplay((await supplierRiskApi.replayOptions(id)).items);
      } catch {}
    } catch (e) {
      setError(e instanceof Error ? e.message : "Execution unavailable");
    }
  }, [id]);
  useEffect(() => {
    const scheduled = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(scheduled);
  }, [load]);
  useEffect(() => {
    if (!execution || !shouldPoll(String(execution.state), !document.hidden))
      return;
    const scheduled = window.setTimeout(() => void load(), nextPollDelay(1));
    return () => window.clearTimeout(scheduled);
  }, [execution, load]);
  if (error)
    return <RouteState title="Execution unavailable" message={error} />;
  if (!execution)
    return (
      <RouteState
        title="Loading execution"
        message="Retrieving current status…"
      />
    );
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">Logical execution</span>
          <h1>Supplier-risk assessment</h1>
          <p className="mono">{id}</p>
        </div>
        <div className="action-row">
          {retry && (
            <RetryDialog logicalId={id} eligibility={retry} onAccepted={load} />
          )}
          <ReplayDialog logicalId={id} options={replay} onAccepted={load} />
        </div>
      </div>
      <StatusSummary
        execution={String(execution.state)}
        outcome={
          (result?.terminal_classification ??
            execution.terminal_classification ??
            null) as TerminalClassification | null
        }
        stage={stages.at(-1)?.stage_name}
      />
      <div className="two-column">
        <section className="panel">
          <h2>Stage progress</h2>
          <StageTimeline stages={stages} />
        </section>
        <AttemptHistory logicalId={id} attempts={attempts} />
      </div>
      {result ? (
        <RecommendationPanel result={result} />
      ) : (
        <section className="panel" role="status">
          <h2>Recommendation pending</h2>
          <p>The engine has not returned a governed final recommendation.</p>
        </section>
      )}
      <div className="sr-only" aria-live="polite">
        Execution status updated: {String(execution.state)}
      </div>
    </>
  );
}
