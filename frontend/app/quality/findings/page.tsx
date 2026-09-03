"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { EmptyState } from "@/components/design-system/empty-state";
import { PageHeader } from "@/components/design-system/page-header";
import { OqiApiError, oqiApi } from "@/lib/oqi/api-client";
import type { FindingSummary } from "@/lib/oqi/contracts";

// CDD-045 §10/§25-26: the Finding list respects the API's own pagination
// contract (no "fetch everything") and offers only the filters the API
// itself supports (family, status). There is no composite priority score --
// criticality, Reliance, and age remain visible as separate, independent
// columns a user can scan, never blended into one ranking (CDD-045 §26).
const RELIANCE_LABEL: Record<string, string> = {
  RELIANCE_SUPPORTED: "Reliance Supported",
  RELIANCE_AT_RISK: "Reliance At Risk",
  RELIANCE_UNKNOWN: "Reliance Unknown",
};

type LoadState =
  | { status: "loading"; cursor: string | null }
  | {
      status: "loaded";
      items: FindingSummary[];
      nextCursor: string | null;
      cursor: string | null;
    }
  | { status: "unauthorized" }
  | { status: "error"; code: string };

// Next.js requires any component reading useSearchParams() to render inside a
// Suspense boundary (missing-suspense-with-csr-bailout) -- this is a render-
// boundary requirement only; it changes nothing about OQI truth, filtering,
// or URL/deep-link behavior, all of which live in FindingsPageContent below.
export default function FindingsPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-5xl">
          <PageHeader
            eyebrow="Ontology Quality Intelligence"
            title="Findings"
          />
          <EmptyState kind="loading" title="Loading Findings" />
        </div>
      }
    >
      <FindingsPageContent />
    </Suspense>
  );
}

function FindingsPageContent() {
  const searchParams = useSearchParams();
  const initialStatus = searchParams.get("status") ?? "";
  const [family, setFamily] = useState("");
  const [status, setStatus] = useState(initialStatus);
  const [state, setState] = useState<LoadState>({
    status: "loading",
    cursor: null,
  });

  const load = useCallback(
    (cursorValue: string | null) => {
      setState({ status: "loading", cursor: cursorValue });
      oqiApi
        .listFindings({
          family: family || undefined,
          status: status || undefined,
          cursor: cursorValue ?? undefined,
        })
        .then((response) =>
          setState({
            status: "loaded",
            items: response.items,
            nextCursor: response.next_cursor,
            cursor: cursorValue,
          }),
        )
        .catch((caught) => {
          if (caught instanceof OqiApiError) {
            if (caught.status === 401 || caught.status === 403) {
              setState({ status: "unauthorized" });
              return;
            }
            setState({ status: "error", code: caught.code });
            return;
          }
          setState({ status: "error", code: "UNKNOWN_ERROR" });
        });
    },
    [family, status],
  );

  useEffect(() => {
    // Defer past this effect's own synchronous execution: load() itself sets
    // state, and calling it synchronously here would trigger a same-commit
    // re-render (react-hooks/set-state-in-effect). Queuing it as a microtask
    // keeps identical fetch/filter/URL behavior while letting this effect's
    // own commit finish first.
    queueMicrotask(() => load(null));
  }, [load]);

  return (
    <div className="max-w-5xl">
      <PageHeader eyebrow="Ontology Quality Intelligence" title="Findings" />

      <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
        <label>
          Quality family
          <select
            aria-label="Quality family"
            value={family}
            onChange={(event) => setFamily(event.target.value)}
            style={{ marginLeft: "0.5rem" }}
          >
            <option value="">All families</option>
            <option value="OQI1">Completeness / Validity</option>
            <option value="OQI2">Cross-Source Consistency</option>
            <option value="OQI3">Business Rules</option>
            <option value="INTEGRITY">Integrity</option>
            <option value="TIMELINESS">Timeliness</option>
          </select>
        </label>
        <label>
          Status
          <select
            aria-label="Status"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            style={{ marginLeft: "0.5rem" }}
          >
            <option value="">All statuses</option>
            <option value="OPEN">Open</option>
            <option value="RESOLVED">Resolved</option>
          </select>
        </label>
      </div>

      {state.status === "loading" && (
        <EmptyState kind="loading" title="Loading Findings" />
      )}

      {state.status === "unauthorized" && (
        <EmptyState
          kind="error"
          title="Not authorized to view Findings"
          message="This does not indicate anything about the underlying quality state."
        />
      )}

      {state.status === "error" && (
        <EmptyState
          kind="error"
          title="Findings are temporarily unavailable"
          message={`Backend unavailable (${state.code}).`}
        />
      )}

      {state.status === "loaded" && state.items.length === 0 && (
        <EmptyState
          kind="empty"
          title="No Findings match this view"
          message="This does not by itself establish complete quality coverage."
        />
      )}

      {state.status === "loaded" && state.items.length > 0 && (
        <>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left" }}>Condition</th>
                <th style={{ textAlign: "left" }}>Family</th>
                <th style={{ textAlign: "left" }}>Status</th>
                <th style={{ textAlign: "left" }}>Criticality</th>
                <th style={{ textAlign: "left" }}>Reliance</th>
                <th style={{ textAlign: "left" }}>Last seen</th>
              </tr>
            </thead>
            <tbody>
              {state.items.map((item) => (
                <tr key={item.finding_id}>
                  <td>
                    <Link href={`/quality/findings/${item.finding_id}`}>
                      {item.condition_label}
                    </Link>
                  </td>
                  <td>{item.finding_family}</td>
                  <td>{item.status}</td>
                  <td>{item.highest_criticality ?? "Unknown"}</td>
                  <td>
                    {item.reliance_state
                      ? (RELIANCE_LABEL[item.reliance_state] ??
                        item.reliance_state)
                      : "Reliance Unknown"}
                  </td>
                  <td>{new Date(item.last_seen_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem" }}>
            <button
              className="button"
              disabled={!state.cursor}
              onClick={() => load(null)}
            >
              First page
            </button>
            <button
              className="button"
              disabled={!state.nextCursor}
              onClick={() => {
                if (state.nextCursor) {
                  load(state.nextCursor);
                }
              }}
            >
              Next page
            </button>
          </div>
        </>
      )}
    </div>
  );
}
