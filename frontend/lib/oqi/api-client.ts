import { accessToken } from "@/lib/auth/browser-session";
import { browserAuthConfig } from "@/lib/auth/config";
import type {
  AgentInvestigationResponse,
  BusinessImpactResponse,
  CommandCenterResponse,
  DecideAuthorizationRequest,
  EvidenceResponse,
  FindingDetailResponse,
  FindingListResponse,
  OntologyImpactResponse,
  RelianceResponse,
  RemediationCaseActionResponse,
  RemediationResponse,
} from "./contracts";

// `/api/v1/oqi` has no entry in `_STABLE_ERROR_CONTRACT_PATHS`, so FastAPI's
// default handler applies: failures arrive as `{"detail": {"code": "..."}}`
// -- identical shape to the Evidence Fitness client this mirrors.
export class OqiApiError extends Error {
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

async function request<T>(
  path: string,
  init?: RequestInit,
  signal?: AbortSignal,
): Promise<T> {
  const token = await accessToken();
  if (!token) throw new OqiApiError("AUTH_REQUIRED", 401);

  const response = await fetch(`${browserAuthConfig().apiOrigin}${path}`, {
    ...init,
    signal,
    cache: "no-store",
    credentials: "omit",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const parsed = await response.json().catch(() => null);
    throw new OqiApiError(
      parsed ? extractCode(parsed) : `HTTP_${response.status}`,
      response.status,
    );
  }

  return (await response.json()) as T;
}

export const oqiApi = {
  commandCenter: (signal?: AbortSignal): Promise<CommandCenterResponse> =>
    request<CommandCenterResponse>(
      "/api/v1/oqi/command-center",
      undefined,
      signal,
    ),

  listFindings: (
    params: {
      family?: string;
      status?: string;
      cursor?: string;
      limit?: number;
    },
    signal?: AbortSignal,
  ): Promise<FindingListResponse> => {
    const query = new URLSearchParams();
    if (params.family) query.set("family", params.family);
    if (params.status) query.set("status", params.status);
    if (params.cursor) query.set("cursor", params.cursor);
    if (params.limit) query.set("limit", String(params.limit));
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return request<FindingListResponse>(
      `/api/v1/oqi/findings${suffix}`,
      undefined,
      signal,
    );
  },

  findingDetail: (
    findingId: string,
    signal?: AbortSignal,
  ): Promise<FindingDetailResponse> =>
    request<FindingDetailResponse>(
      `/api/v1/oqi/findings/${findingId}`,
      undefined,
      signal,
    ),

  evidence: (
    findingId: string,
    signal?: AbortSignal,
  ): Promise<EvidenceResponse> =>
    request<EvidenceResponse>(
      `/api/v1/oqi/findings/${findingId}/evidence`,
      undefined,
      signal,
    ),

  ontologyImpact: (
    findingId: string,
    signal?: AbortSignal,
  ): Promise<OntologyImpactResponse> =>
    request<OntologyImpactResponse>(
      `/api/v1/oqi/findings/${findingId}/ontology-impact`,
      undefined,
      signal,
    ),

  businessImpact: (
    findingId: string,
    signal?: AbortSignal,
  ): Promise<BusinessImpactResponse> =>
    request<BusinessImpactResponse>(
      `/api/v1/oqi/findings/${findingId}/business-impact`,
      undefined,
      signal,
    ),

  reliance: (
    findingId: string,
    signal?: AbortSignal,
  ): Promise<RelianceResponse> =>
    request<RelianceResponse>(
      `/api/v1/oqi/findings/${findingId}/reliance`,
      undefined,
      signal,
    ),

  agentInvestigation: (
    findingId: string,
    signal?: AbortSignal,
  ): Promise<AgentInvestigationResponse> =>
    request<AgentInvestigationResponse>(
      `/api/v1/oqi/findings/${findingId}/agent-investigation`,
      undefined,
      signal,
    ),

  remediation: (
    findingId: string,
    signal?: AbortSignal,
  ): Promise<RemediationResponse> =>
    request<RemediationResponse>(
      `/api/v1/oqi/findings/${findingId}/remediation`,
      undefined,
      signal,
    ),

  decideAuthorization: (
    authorizationId: string,
    body: DecideAuthorizationRequest,
  ): Promise<RemediationCaseActionResponse> =>
    request<RemediationCaseActionResponse>(
      `/api/v1/oqi/remediation/authorizations/${authorizationId}/decide`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  reportExecution: (
    authorizationId: string,
  ): Promise<RemediationCaseActionResponse> =>
    request<RemediationCaseActionResponse>(
      `/api/v1/oqi/remediation/authorizations/${authorizationId}/report-execution`,
      { method: "POST", body: JSON.stringify({}) },
    ),
};
