import type { Connector, OntologyDetail } from "./contracts";

export class OntologyApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

function apiOrigin(): string {
  return process.env.NEXT_PUBLIC_CTEC_API_ORIGIN ?? "";
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${apiOrigin()}/api/v1/ontologies${path}`);
  if (!response.ok) {
    throw new OntologyApiError(
      response.status,
      `Ontology service request failed (${response.status})`,
    );
  }
  return (await response.json()) as T;
}

export const ontologyApi = {
  getOntology: (ontologyId: string) =>
    request<OntologyDetail>(`/${ontologyId}`),
  getOntologyVersion: (ontologyId: string, version: string) =>
    request<OntologyDetail>(`/${ontologyId}/versions/${version}`),
  getExportPreview: (ontologyId: string) =>
    request<Record<string, unknown>>(`/${ontologyId}/export?format=json-ld`),
  getConnectors: () =>
    request<{ connectors: Connector[] }>(`/connectors/catalog`),
};
