import { accessToken } from "@/lib/auth/browser-session";
import { browserAuthConfig } from "@/lib/auth/config";
import type {
  ApiProblemBody,
  SupplyChainImpactEvaluateRequestBody,
  SupplyChainImpactEvaluateResponse,
  SupplyChainImpactReadResponse,
} from "./contracts";

export class SupplyChainImpactApiError extends Error {
  constructor(
    public code: string,
    public status: number,
  ) {
    super(code);
  }
}

function problemCode(body: unknown): string {
  const problem = body as ApiProblemBody | undefined;
  if (problem && "detail" in problem) {
    const { detail } = problem;
    if (detail && typeof detail === "object" && "code" in detail) {
      return detail.code;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      return detail[0]?.type ?? "VALIDATION_ERROR";
    }
  }
  return "UNKNOWN_ERROR";
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  signal?: AbortSignal,
): Promise<T> {
  const token = await accessToken();
  if (!token) throw new SupplyChainImpactApiError("AUTH_TOKEN_MISSING", 401);
  const response = await fetch(
    `${browserAuthConfig().apiOrigin}/api/v1/supply-chain-impact${path}`,
    {
      ...init,
      signal,
      cache: "no-store",
      credentials: "omit",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
        ...init.headers,
      },
    },
  );
  if (!response.ok) {
    const body = await response.json().catch(() => undefined);
    throw new SupplyChainImpactApiError(problemCode(body), response.status);
  }
  return response.json() as Promise<T>;
}

export const supplyChainImpactApi = {
  // The browser identifies only the evaluation target -- it can never
  // send tenant, risk severity, single-source result, revenue exposure,
  // materiality, qualification, capacity, lead time, cost,
  // recommendation, or governance outcome. The backend's own
  // `extra="forbid"` request schema rejects any other field even if this
  // client attempted to send one (CDD-016 §23).
  evaluate: (supplierEntityId: string, signal?: AbortSignal) =>
    request<SupplyChainImpactEvaluateResponse>(
      "/evaluations",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          supplier_entity_id: supplierEntityId,
        } satisfies SupplyChainImpactEvaluateRequestBody),
      },
      signal,
    ),
  read: (decisionEvaluationId: string, signal?: AbortSignal) =>
    request<SupplyChainImpactReadResponse>(
      `/evaluations/${decisionEvaluationId}`,
      { method: "GET" },
      signal,
    ),
};
