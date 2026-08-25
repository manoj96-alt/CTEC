import { accessToken } from "@/lib/auth/browser-session";
import { browserAuthConfig } from "@/lib/auth/config";
import type { ResolveRequest, ResolveResponse } from "./contracts";

// The Information-Element Context path is not one of backend/app/main.py's
// `_STABLE_ERROR_CONTRACT_PATHS`, so FastAPI's default handler applies:
// failures arrive as `{"detail": {"code": "..."}}`, with no `message`,
// `correlation_id`, or `retryable` field. This client reflects that real
// shape rather than the richer envelope other domains' clients parse.
export class ContextApiError extends Error {
  constructor(
    public code: string,
    public status: number,
  ) {
    super(code);
  }
}

function extractCode(body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (detail && typeof detail === "object" && "code" in detail) {
      const code = (detail as { code: unknown }).code;
      if (typeof code === "string") return code;
    }
  }
  return "REQUEST_REJECTED";
}

export const contextApi = {
  resolve: async (
    body: ResolveRequest,
    signal?: AbortSignal,
  ): Promise<ResolveResponse> => {
    const token = await accessToken();
    if (!token) throw new ContextApiError("AUTH_REQUIRED", 401);

    const response = await fetch(
      `${browserAuthConfig().apiOrigin}/api/v1/information-element-context/resolve`,
      {
        method: "POST",
        signal,
        cache: "no-store",
        credentials: "omit",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body satisfies ResolveRequest),
      },
    );

    if (!response.ok) {
      const parsed = await response.json().catch(() => null);
      throw new ContextApiError(
        parsed ? extractCode(parsed) : `HTTP_${response.status}`,
        response.status,
      );
    }

    return (await response.json()) as ResolveResponse;
  },
};
