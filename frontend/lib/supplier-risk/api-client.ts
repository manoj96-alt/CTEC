import { accessToken } from "@/lib/auth/browser-session";
import { browserAuthConfig } from "@/lib/auth/config";
import type {
  ApiProblem,
  ExecutionList,
  GovernedResult,
  ReplayOption,
  RetryEligibility,
  Stage,
  SubmissionResponse,
} from "./contracts";

export class SupplierRiskApiError extends Error {
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
    throw new SupplierRiskApiError(
      {
        code: "AUTH_REQUIRED",
        message: "Sign in is required",
        correlation_id: crypto.randomUUID(),
        retryable: false,
      },
      401,
    );
  const response = await fetch(
    `${browserAuthConfig().apiOrigin}/api/v1/supplier-risk${path}`,
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
    throw new SupplierRiskApiError(
      (await response.json().catch(() => fallback)) as ApiProblem,
      response.status,
    );
  }
  return response.status === 202 &&
    response.headers.get("content-length") === "0"
    ? (null as T)
    : (response.json() as Promise<T>);
}
export const supplierRiskApi = {
  queue: (cursor?: string, signal?: AbortSignal) =>
    request<ExecutionList>(
      `/executions?limit=25${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`,
      {},
      signal,
    ),
  execution: (id: string, signal?: AbortSignal) =>
    request<Record<string, unknown>>(
      `/executions/${encodeURIComponent(id)}`,
      {},
      signal,
    ),
  attempts: (id: string, signal?: AbortSignal) =>
    request<{ items: Record<string, unknown>[]; next_cursor: string | null }>(
      `/executions/${encodeURIComponent(id)}/attempts`,
      {},
      signal,
    ),
  stages: (logical: string, attempt: string, signal?: AbortSignal) =>
    request<{ items: Stage[] }>(
      `/executions/${encodeURIComponent(logical)}/attempts/${encodeURIComponent(attempt)}/stages`,
      {},
      signal,
    ),
  result: (id: string, signal?: AbortSignal) =>
    request<GovernedResult | null>(
      `/executions/${encodeURIComponent(id)}/result`,
      {},
      signal,
    ),
  retryEligibility: (id: string) =>
    request<RetryEligibility>(
      `/executions/${encodeURIComponent(id)}/retry-eligibility`,
    ),
  replayOptions: (id: string) =>
    request<{ items: ReplayOption[] }>(
      `/executions/${encodeURIComponent(id)}/replay-options`,
    ),
  submit: (body: object, requestId: string) =>
    request<SubmissionResponse>("/assessments", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": requestId,
      },
      body: JSON.stringify(body),
    }),
  retry: (id: string, body: object, requestId: string) =>
    request<SubmissionResponse>(`/executions/${encodeURIComponent(id)}/retry`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": requestId,
      },
      body: JSON.stringify(body),
    }),
  replay: (id: string, body: object, requestId: string) =>
    request<SubmissionResponse>(
      `/executions/${encodeURIComponent(id)}/replay`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": requestId,
        },
        body: JSON.stringify(body),
      },
    ),
};
