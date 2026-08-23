import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeAll, beforeEach, expect, test, vi } from "vitest";
import { OntologyModelingWorkspace } from "@/app/ontology-studio/ontology-modeling/_components/ontology-modeling-workspace";
import { OntologyModelingApiError } from "@/lib/ontology-modeling/api-client";

const {
  getOntologyMock,
  listProposalsMock,
  proposeConceptMock,
  proposeRelationshipMock,
  approveMock,
  rejectMock,
  publishMock,
} = vi.hoisted(() => ({
  getOntologyMock: vi.fn(),
  listProposalsMock: vi.fn(),
  proposeConceptMock: vi.fn(),
  proposeRelationshipMock: vi.fn(),
  approveMock: vi.fn(),
  rejectMock: vi.fn(),
  publishMock: vi.fn(),
}));

vi.mock("@/lib/ontology-studio/api-client", () => ({
  ontologyApi: { getOntology: getOntologyMock },
}));

vi.mock("@/lib/ontology-modeling/api-client", async () => {
  const actual = await vi.importActual<
    typeof import("@/lib/ontology-modeling/api-client")
  >("@/lib/ontology-modeling/api-client");
  return {
    ...actual,
    ontologyModelingApi: {
      listProposals: listProposalsMock,
      proposeConcept: proposeConceptMock,
      proposeRelationship: proposeRelationshipMock,
      approve: approveMock,
      reject: rejectMock,
      publish: publishMock,
    },
  };
});

beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
});

beforeEach(() => {
  getOntologyMock.mockReset();
  listProposalsMock.mockReset();
  proposeConceptMock.mockReset();
  proposeRelationshipMock.mockReset();
  approveMock.mockReset();
  rejectMock.mockReset();
  publishMock.mockReset();
});

const ontologyDetail = {
  ontology_id: "supplier-risk",
  name: "Supplier Risk",
  description: "",
  version: "1",
  status: "Published",
  concepts: [
    {
      entity_type_id: "concept-1",
      name: "Supplier",
      definition: "",
      definition_source: "curated",
      lifecycle_state: "Active",
      governance_status: "Approved",
      version_number: 1,
      discovery_label: "",
    },
  ],
  relationships: [],
  source_mappings: [],
  provenance: "",
  governance_metadata: "",
  quality: {
    overall_score: 1,
    method: "",
    dimensions: [],
    passed_checks: [],
    failed_checks: [],
  },
  activation_applications: 0,
};

function proposal(overrides: Record<string, unknown> = {}) {
  return {
    ontology_change_proposal_id: "proposal-1",
    proposal_kind: "CreateConcept",
    status: "Proposed",
    proposed_entity_type_name: "Warehouse",
    proposed_definition: null,
    proposed_relationship_type_name: null,
    proposed_source_entity_type_id: null,
    proposed_target_entity_type_id: null,
    proposed_by: "user-jane",
    proposed_on: "2026-01-01T00:00:00Z",
    approved_by: null,
    approved_on: null,
    rejected_by: null,
    rejected_on: null,
    rejection_reason: null,
    published_by: null,
    published_on: null,
    published_entity_type_id: null,
    published_relationship_type_id: null,
    ...overrides,
  };
}

test("renders the propose form once the governed ontology loads, and submits a Concept proposal", async () => {
  getOntologyMock.mockResolvedValue(ontologyDetail);
  listProposalsMock.mockResolvedValue({ proposals: [] });
  proposeConceptMock.mockResolvedValue(proposal());

  render(<OntologyModelingWorkspace />);

  await waitFor(() =>
    expect(screen.getByText("Propose a net-new object")).toBeInTheDocument(),
  );

  fireEvent.change(screen.getByLabelText("Concept name"), {
    target: { value: "Warehouse" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Submit proposal" }));

  await waitFor(() =>
    expect(proposeConceptMock).toHaveBeenCalledWith({
      proposal_kind: "CreateConcept",
      entity_type_name: "Warehouse",
      definition: null,
    }),
  );
  // No direct canonical-mutation call of any kind is ever made from this
  // component -- only the six /api/v1/ontology-modeling/* methods above.
  expect(getOntologyMock).toHaveBeenCalledTimes(1);
});

test("populates the Relationship source/target dropdowns from the read-only ontology", async () => {
  getOntologyMock.mockResolvedValue(ontologyDetail);
  listProposalsMock.mockResolvedValue({ proposals: [] });

  render(<OntologyModelingWorkspace />);
  await waitFor(() =>
    expect(screen.getByText("Propose a net-new object")).toBeInTheDocument(),
  );

  fireEvent.click(screen.getByLabelText("New Relationship"));

  expect(screen.getAllByText("Supplier", { selector: "option" })).toHaveLength(
    2,
  );
});

test("shows fetched proposals and their status", async () => {
  getOntologyMock.mockResolvedValue(ontologyDetail);
  listProposalsMock.mockResolvedValue({ proposals: [proposal()] });

  render(<OntologyModelingWorkspace />);

  await waitFor(() =>
    expect(screen.getByText("Warehouse")).toBeInTheDocument(),
  );
  expect(screen.getByText("Proposed")).toBeInTheDocument();
});

test("approve/reject are unavailable once a proposal is no longer Proposed", async () => {
  getOntologyMock.mockResolvedValue(ontologyDetail);
  listProposalsMock.mockResolvedValue({
    proposals: [proposal({ status: "Approved" })],
  });

  render(<OntologyModelingWorkspace />);
  await waitFor(() =>
    expect(screen.getByText("Warehouse")).toBeInTheDocument(),
  );

  expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Reject" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Publish" })).not.toBeDisabled();
});

test("publish is unavailable when only Proposed (never implicitly authorized by approve alone)", async () => {
  getOntologyMock.mockResolvedValue(ontologyDetail);
  listProposalsMock.mockResolvedValue({ proposals: [proposal()] });

  render(<OntologyModelingWorkspace />);
  await waitFor(() =>
    expect(screen.getByText("Warehouse")).toBeInTheDocument(),
  );

  expect(screen.getByRole("button", { name: "Publish" })).toBeDisabled();
});

test("a 409 conflict on approve shows the reload-proposals prompt, not a raw error", async () => {
  getOntologyMock.mockResolvedValue(ontologyDetail);
  listProposalsMock.mockResolvedValue({ proposals: [proposal()] });
  approveMock.mockRejectedValue(
    new OntologyModelingApiError("INVALID_PROPOSAL_TRANSITION", 409),
  );

  render(<OntologyModelingWorkspace />);
  await waitFor(() =>
    expect(screen.getByText("Warehouse")).toBeInTheDocument(),
  );

  fireEvent.click(screen.getByRole("button", { name: "Approve" }));
  fireEvent.click(screen.getByRole("button", { name: "Confirm: Approve" }));

  await waitFor(() =>
    expect(screen.getByText("This proposal has changed")).toBeInTheDocument(),
  );
});

test("a 403 on publish surfaces AUTHORIZATION_SCOPE_REQUIRED, never a silent success", async () => {
  getOntologyMock.mockResolvedValue(ontologyDetail);
  listProposalsMock.mockResolvedValue({
    proposals: [proposal({ status: "Approved" })],
  });
  publishMock.mockRejectedValue(
    new OntologyModelingApiError("AUTHORIZATION_SCOPE_REQUIRED", 403),
  );

  render(<OntologyModelingWorkspace />);
  await waitFor(() =>
    expect(screen.getByText("Warehouse")).toBeInTheDocument(),
  );

  fireEvent.click(screen.getByRole("button", { name: "Publish" }));
  fireEvent.click(screen.getByRole("button", { name: "Confirm: Publish" }));

  await waitFor(() =>
    expect(
      screen.getByText("AUTHORIZATION_SCOPE_REQUIRED"),
    ).toBeInTheDocument(),
  );
});

test("shows an unauthorized state for the proposal list when no token is present", async () => {
  getOntologyMock.mockResolvedValue(ontologyDetail);
  listProposalsMock.mockRejectedValue(
    new OntologyModelingApiError("AUTH_REQUIRED", 401),
  );

  render(<OntologyModelingWorkspace />);

  await waitFor(() =>
    expect(
      screen.getByText(
        "Sign in is required to view ontology modeling proposals.",
      ),
    ).toBeInTheDocument(),
  );
});
