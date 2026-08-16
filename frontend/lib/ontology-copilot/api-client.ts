import { accessToken } from "@/lib/auth/browser-session";
import { browserAuthConfig } from "@/lib/auth/config";
import type { ApiProblem, AskRequestBody, AskResponse } from "./contracts";

export class OntologyCopilotApiError extends Error {
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
    throw new OntologyCopilotApiError(
      {
        code: "AUTH_REQUIRED",
        message: "Sign in is required",
        correlation_id: crypto.randomUUID(),
        retryable: false,
      },
      401,
    );
  const response = await fetch(
    `${browserAuthConfig().apiOrigin}/api/v1/ontology-copilot${path}`,
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
    throw new OntologyCopilotApiError(
      (await response.json().catch(() => fallback)) as ApiProblem,
      response.status,
    );
  }
  return response.json() as Promise<T>;
}

export const ontologyCopilotApi = {
  ask: (body: AskRequestBody, signal?: AbortSignal) =>
    request<AskResponse>(
      "/ask",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
      signal,
    ),
};
