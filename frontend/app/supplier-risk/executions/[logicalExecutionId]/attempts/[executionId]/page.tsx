"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { StageTimeline } from "@/components/supplier-risk/stage-timeline";
import { RouteState } from "@/components/supplier-risk/route-state";
import { supplierRiskApi } from "@/lib/supplier-risk/api-client";
import type { Stage } from "@/lib/supplier-risk/contracts";
export default function AttemptPage() {
  const { logicalExecutionId, executionId } = useParams<{
    logicalExecutionId: string;
    executionId: string;
  }>();
  const [stages, setStages] = useState<Stage[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    supplierRiskApi
      .stages(logicalExecutionId, executionId, controller.signal)
      .then((v) => setStages(v.items))
      .catch((e) => setError(e.message));
    return () => controller.abort();
  }, [logicalExecutionId, executionId]);
  if (error) return <RouteState title="Attempt unavailable" message={error} />;
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">Execution attempt</span>
          <h1>Capability progress</h1>
          <p className="mono">{executionId}</p>
        </div>
      </div>
      <section className="panel">
        {stages ? (
          <StageTimeline stages={stages} />
        ) : (
          <p role="status">Loading stage progress…</p>
        )}
      </section>
    </>
  );
}
