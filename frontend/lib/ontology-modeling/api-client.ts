import { accessToken } from "@/lib/auth/browser-session";
import { browserAuthConfig } from "@/lib/auth/config";
import type {
  OntologyModelingProblem,
  ProposalDetail,
  ProposalList,
  ProposalStatus,
  ProposeConceptBody,
  ProposeRelationshipBody,
  RejectBody,
} from "./contracts";

export class OntologyModelingApiError extends Error {
  constructor(
    public code: string,
    public status: number,
  ) {
    super(code);
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  signal?: AbortSignal,
): Promise<T> {
  const token = await accessToken();
  if (!token) throw new OntologyModelingApiError("AUTH_REQUIRED", 401);
  const response = await fetch(
    `${browserAuthConfig().apiOrigin}/api/v1/ontology-modeling${path}`,
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
    const body = await response
      .json()
      .catch(() => ({ detail: { code: `HTTP_${response.status}` } }));
    const problem = (body?.detail ?? {
      code: `HTTP_${response.status}`,
    }) as OntologyModelingProblem;
    throw new OntologyModelingApiError(problem.code, response.status);
  }
  return response.json() as Promise<T>;
}

export const ontologyModelingApi = {
  proposeConcept: (body: ProposeConceptBody, signal?: AbortSignal) =>
    request<ProposalDetail>(
      "/proposals",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
      signal,
    ),
  proposeRelationship: (body: ProposeRelationshipBody, signal?: AbortSignal) =>
    request<ProposalDetail>(
      "/proposals",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
      signal,
    ),
  listProposals: (status?: ProposalStatus, signal?: AbortSignal) =>
    request<ProposalList>(
      status ? `/proposals?status=${encodeURIComponent(status)}` : "/proposals",
      {},
      signal,
    ),
  getProposal: (id: string, signal?: AbortSignal) =>
    request<ProposalDetail>(`/proposals/${encodeURIComponent(id)}`, {}, signal),
  approve: (id: string, signal?: AbortSignal) =>
    request<ProposalDetail>(
      `/proposals/${encodeURIComponent(id)}/approve`,
      { method: "POST" },
      signal,
    ),
  reject: (id: string, body: RejectBody, signal?: AbortSignal) =>
    request<ProposalDetail>(
      `/proposals/${encodeURIComponent(id)}/reject`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
      signal,
    ),
  publish: (id: string, signal?: AbortSignal) =>
    request<ProposalDetail>(
      `/proposals/${encodeURIComponent(id)}/publish`,
      { method: "POST" },
      signal,
    ),
};
