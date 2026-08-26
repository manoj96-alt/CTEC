"use client";

import { useEffect, useState } from "react";
import { AssessmentTable } from "@/components/supplier-risk/assessment-table";
import { RouteState } from "@/components/supplier-risk/route-state";
import { PageHeader } from "@/components/design-system/page-header";
import { supplierRiskApi } from "@/lib/supplier-risk/api-client";
import type { ExecutionList } from "@/lib/supplier-risk/contracts";

// Frontend-only aggregation of existing Gate F execution history (CDD-033
// §19). Reuses the existing, unmodified `supplierRiskApi.queue()` client
// and `AssessmentTable` component verbatim -- no new decision concept, no
// Gate T/Gate U join (CDD-033 §20).
export default function Page() {
  const [data, setData] = useState<ExecutionList | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    supplierRiskApi
      .queue(undefined, controller.signal)
      .then(setData)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => controller.abort();
  }, []);

  return (
    <div className="max-w-5xl">
      <PageHeader
        eyebrow="Intelligence"
        title="Decisions"
        description="Existing Gate F governed supplier-risk decision history, presented as a cross-cutting view."
      />
      {error ? (
        <RouteState title="Decisions unavailable" message={error} />
      ) : data ? (
        <AssessmentTable items={data.items} />
      ) : (
        <p>Loading…</p>
      )}
    </div>
  );
}
