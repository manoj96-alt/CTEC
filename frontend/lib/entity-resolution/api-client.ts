import { accessToken } from "@/lib/auth/browser-session";
import { browserAuthConfig } from "@/lib/auth/config";
import type {
  ApiProblem,
  CaseDetail,
  CaseList,
  DecisionRequestBody,
  DecisionResult,
  PolicyList,
  PreviewResult,
} from "./contracts";

export class EntityResolutionApiError extends Error {
  constructor(
    public problem: ApiProblem,
    public status: number,
  ) {
    super(problem.message);
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  signal?: AbortSignal,
): Promise<T> {
  const token = await accessToken();
  if (!token)
    throw new EntityResolutionApiError(
      {
        code: "AUTH_REQUIRED",
        message: "Sign in is required",
        correlation_id: crypto.randomUUID(),
        retryable: false,
      },
      401,
    );
  const response = await fetch(
    `${browserAuthConfig().apiOrigin}/api/v1/entity-resolution${path}`,
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
    const fallback: ApiProblem = {
      code: `HTTP_${response.status}`,
      message: "Request could not be completed",
      correlation_id: crypto.randomUUID(),
      retryable: response.status >= 500,
    };
    throw new EntityResolutionApiError(
      (await response.json().catch(() => fallback)) as ApiProblem,
      response.status,
    );
  }
  return response.json() as Promise<T>;
}

export const entityResolutionApi = {
  queue: (outcome?: string, signal?: AbortSignal) =>
    request<CaseList>(
      outcome ? `/cases?outcome=${encodeURIComponent(outcome)}` : "/cases",
      {},
      signal,
    ),
  caseDetail: (understandingKey: string, signal?: AbortSignal) =>
    request<CaseDetail>(
      `/cases/${encodeURIComponent(understandingKey)}`,
      {},
      signal,
    ),
  policies: (signal?: AbortSignal) =>
    request<PolicyList>("/policies", {}, signal),
  preview: (understandingKey: string, policyId: string, signal?: AbortSignal) =>
    request<PreviewResult>(
      `/cases/${encodeURIComponent(understandingKey)}/preview?policy_id=${encodeURIComponent(policyId)}`,
      { method: "POST" },
      signal,
    ),
  decide: (
    understandingKey: string,
    body: DecisionRequestBody,
    signal?: AbortSignal,
  ) =>
    request<DecisionResult>(
      `/cases/${encodeURIComponent(understandingKey)}/decisions`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
      signal,
    ),
};
