"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { AssessmentTable } from "@/components/supplier-risk/assessment-table";
import { RouteState } from "@/components/supplier-risk/route-state";
import { supplierRiskApi } from "@/lib/supplier-risk/api-client";
import type { ExecutionList } from "@/lib/supplier-risk/contracts";
export default function SupplierRiskPage() {
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
  if (error)
    return <RouteState title="Assessments unavailable" message={error} />;
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">Supplier risk</span>
          <h1>Assessment work queue</h1>
          <p>
            Track governed assessments and the action each recommendation
            permits.
          </p>
        </div>
        <Link className="button" href="/supplier-risk/new">
          New assessment
        </Link>
      </div>
      {data ? (
        <AssessmentTable items={data.items} />
      ) : (
        <RouteState
          title="Loading assessments"
          message="Retrieving the current tenant work queue…"
        />
      )}
    </>
  );
}
