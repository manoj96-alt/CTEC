"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/design-system/page-header";
import { browserAuthConfig } from "@/lib/auth/config";

// ADMINISTRATION boundary (CDD-033 §24): "System Health" presents only the
// existing, unmodified `GET /health` liveness signal, honestly labeled as
// basic liveness (not per-service/connector health detail, which does not
// exist). "Users & Access" does not appear -- no CTEC-owned user/role API
// exists; identity is fully delegated to the OIDC provider.
type HealthState =
  | { status: "loading" }
  | { status: "healthy" }
  | { status: "error"; message: string };

export default function Page() {
  const [health, setHealth] = useState<HealthState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${browserAuthConfig().apiOrigin}/health`, {
      signal: controller.signal,
      cache: "no-store",
    })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json() as Promise<{ status: string }>;
      })
      .then((body) => {
        setHealth(
          body.status === "healthy"
            ? { status: "healthy" }
            : { status: "error", message: body.status },
        );
      })
      .catch((e) => {
        if (e.name !== "AbortError") {
          setHealth({ status: "error", message: e.message });
        }
      });
    return () => controller.abort();
  }, []);

  return (
    <div className="max-w-5xl">
      <PageHeader eyebrow="Administration" title="Administration" />

      <section className="panel">
        <span className="eyebrow">System Health</span>
        <h2>
          {health.status === "loading"
            ? "Checking…"
            : health.status === "healthy"
              ? "Healthy"
              : "Unavailable"}
        </h2>
        <p style={{ color: "var(--muted)" }}>
          Basic backend liveness only. Per-service or per-connector health
          detail is not available.
        </p>
        {health.status === "error" ? (
          <p style={{ color: "var(--muted)" }}>{health.message}</p>
        ) : null}
      </section>

      <section className="panel" style={{ marginTop: "1.5rem" }}>
        <span className="eyebrow">Users &amp; Access</span>
        <h2>Not managed by CTEC</h2>
        <p style={{ color: "var(--muted)" }}>
          CTEC has no user, role, or tenant management capability of its own.
          Identity, authentication, and authorization are fully delegated to the
          identity provider.
        </p>
      </section>
    </div>
  );
}
