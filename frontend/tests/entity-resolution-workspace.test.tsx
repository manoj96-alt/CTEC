import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeAll, beforeEach, expect, test, vi } from "vitest";
import { EntityResolutionWorkspace } from "@/app/ontology-studio/entity-resolution/_components/entity-resolution-workspace";
import { EntityResolutionApiError } from "@/lib/entity-resolution/api-client";

const {
  queueMock,
  caseDetailMock,
  policiesMock,
  previewMock,
  decideMock,
  signInMock,
} = vi.hoisted(() => ({
  queueMock: vi.fn(),
  caseDetailMock: vi.fn(),
  policiesMock: vi.fn(),
  previewMock: vi.fn(),
  decideMock: vi.fn(),
  signInMock: vi.fn(),
}));

vi.mock("@/lib/entity-resolution/api-client", async () => {
  const actual = await vi.importActual<
    typeof import("@/lib/entity-resolution/api-client")
  >("@/lib/entity-resolution/api-client");
  return {
    ...actual,
    entityResolutionApi: {
      queue: queueMock,
      caseDetail: caseDetailMock,
      policies: policiesMock,
      preview: previewMock,
      decide: decideMock,
    },
  };
});

vi.mock("@/lib/auth/browser-session", () => ({
  signIn: signInMock,
}));

beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
});

beforeEach(() => {
  queueMock.mockReset();
  caseDetailMock.mockReset();
  policiesMock.mockReset();
  previewMock.mockReset();
  decideMock.mockReset();
  signInMock.mockReset();
});

const caseSummary = {
  understanding_key: "case-key-1",
  record_id: "record-1",
  outcome: "Possible Resolution",
  business_confidence: "Medium",
  policy_version: "Supplier Resolution — Conservative v1.0",
  produced_at: "2026-01-01T00:00:00Z",
  supporting_source_object_count: 2,
  candidate_enterprise_entity_id: "entity-1",
  candidate_enterprise_entity_name: "TSMC",
};

const caseDetail = {
  understanding_key: "case-key-1",
  record_id: "record-1",
  outcome: "Possible Resolution",
  business_confidence: "Medium",
  structured_reasons: [
    "Corroborating non-name attributes: 3 (policy requires 3)",
  ],
  narrative_explanation:
    "Possible Resolution using policy Supplier Resolution — Conservative v1.0 (score=0.75).",
  produced_at: "2026-01-01T00:00:00Z",
  policy_id: "policy-1",
  policy_name: "Conservative",
  policy_version: "Supplier Resolution — Conservative v1.0",
  evidence_profile: {
    items: [
      {
        evidence_type: "Legal Name",
        compared_attributes: ["Legal Name"],
        normalized_values: ["taiwan semiconductor manufacturing company"],
        classification: "Positive",
        contribution: 0.1,
        explanation: "Legal Name matches the candidate exactly for: Registry.",
        provenance: "Registry",
      },
      {
        evidence_type: "Strong Identifier: Tax/Business Registration",
        compared_attributes: ["Strong Identifier: Tax/Business Registration"],
        normalized_values: [],
        classification: "Missing",
        contribution: 0,
        explanation:
          "Strong Identifier: Tax/Business Registration was not provided by any representation.",
        provenance: "none",
      },
    ],
  },
  candidate_enterprise_entity_id: "entity-1",
  candidate_enterprise_entity_name: "TSMC",
  source_representations: [
    {
      source_object_id: "obj-1",
      source_object_name: "Demo CRM: TSMC",
      source_system_id: "sys-1",
      source_system_name: "Demo CRM",
    },
    {
      source_object_id: "obj-2",
      source_object_name: "Demo Registry: TSMC",
      source_system_id: "sys-2",
      source_system_name: "Demo Corporate Registry",
    },
  ],
  actor_id: null,
  decision_rationale: null,
  prior_decision_count: 0,
  previous_decision: null,
};

const policyList = {
  items: [
    {
      policy_id: "policy-1",
      policy_name: "Conservative",
      policy_version: "Supplier Resolution — Conservative v1.0",
      preset_kind: "Conservative",
      resolved_threshold: 0.92,
      possible_threshold: 0.55,
      high_confidence_threshold: 0.92,
      medium_confidence_threshold: 0.6,
      min_corroborating_attributes: 3,
      country_conflict_severity: "veto",
      parent_subsidiary_conflict_severity: "veto",
    },
    {
      policy_id: "policy-2",
      policy_name: "Balanced",
      policy_version: "Supplier Resolution — Balanced v1.0",
      preset_kind: "Balanced",
      resolved_threshold: 0.85,
      possible_threshold: 0.5,
      high_confidence_threshold: 0.85,
      medium_confidence_threshold: 0.55,
      min_corroborating_attributes: 2,
      country_conflict_severity: "review",
      parent_subsidiary_conflict_severity: "veto",
    },
  ],
};

function apiError(
  code: string,
  message = "Request could not be completed",
  status = 400,
) {
  return new EntityResolutionApiError(
    { code, message, correlation_id: "corr-1", retryable: false },
    status,
  );
}

test("shows a loading state before the queue arrives", () => {
  queueMock.mockReturnValue(new Promise(() => {}));
  render(<EntityResolutionWorkspace />);
  expect(screen.getByRole("status")).toHaveTextContent(
    /Loading the resolution case queue/,
  );
});

test("shows an unauthorized state with a sign-in action when no token is present", async () => {
  queueMock.mockRejectedValue(
    apiError("AUTH_REQUIRED", "Sign in is required", 401),
  );
  render(<EntityResolutionWorkspace />);
  await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  expect(screen.getByText("Sign in required")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(signInMock).toHaveBeenCalledWith("/ontology-studio/entity-resolution");
});

test("shows a bounded error state with Retry when the service is unavailable, never fabricated data", async () => {
  queueMock.mockRejectedValue(
    apiError("HTTP_503", "Request could not be completed", 503),
  );
  render(<EntityResolutionWorkspace />);
  await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  expect(
    screen.getByText(/Entity Resolution service unavailable/),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  expect(screen.queryByText("TSMC")).not.toBeInTheDocument();
});

test("shows an empty queue honestly", async () => {
  queueMock.mockResolvedValue({ items: [] });
  render(<EntityResolutionWorkspace />);
  await waitFor(() =>
    expect(screen.getByText("No cases in this queue")).toBeInTheDocument(),
  );
});

test("renders the queue and, on selection, the case detail with evidence and source representations", async () => {
  queueMock.mockResolvedValue({ items: [caseSummary] });
  caseDetailMock.mockResolvedValue(caseDetail);
  policiesMock.mockResolvedValue(policyList);
  render(<EntityResolutionWorkspace />);

  await waitFor(() =>
    expect(screen.getAllByText("TSMC")[0]).toBeInTheDocument(),
  );
  fireEvent.click(screen.getAllByText("TSMC")[0]);

  await waitFor(() =>
    expect(
      screen.getByText(/Possible Resolution using policy/),
    ).toBeInTheDocument(),
  );
  expect(screen.getByText("Demo CRM: TSMC")).toBeInTheDocument();
  expect(screen.getByText("Demo Registry: TSMC")).toBeInTheDocument();
  expect(screen.getByText("Legal Name")).toBeInTheDocument();
  expect(
    screen.getByText("Strong Identifier: Tax/Business Registration"),
  ).toBeInTheDocument();
});

test("policy preview shows the simulated outcome without applying anything", async () => {
  queueMock.mockResolvedValue({ items: [caseSummary] });
  caseDetailMock.mockResolvedValue(caseDetail);
  policiesMock.mockResolvedValue(policyList);
  previewMock.mockResolvedValue({
    policy_id: "policy-2",
    policy_name: "Balanced",
    policy_version: "Supplier Resolution — Balanced v1.0",
    outcome: "Resolved",
    business_confidence: "High",
    score: 0.91,
    would_change_outcome: true,
    structured_reasons: [
      "Corroborating non-name attributes: 4 (policy requires 2)",
    ],
  });
  render(<EntityResolutionWorkspace />);

  await waitFor(() =>
    expect(screen.getAllByText("TSMC")[0]).toBeInTheDocument(),
  );
  fireEvent.click(screen.getAllByText("TSMC")[0]);
  await waitFor(() =>
    expect(screen.getByText("Preview outcome")).toBeInTheDocument(),
  );

  fireEvent.change(screen.getByLabelText("Policy"), {
    target: { value: "policy-2" },
  });
  fireEvent.click(screen.getByText("Preview outcome"));

  await waitFor(() =>
    expect(screen.getByText("Would change outcome?")).toBeInTheDocument(),
  );
  expect(screen.getByText("Yes")).toBeInTheDocument();
  expect(previewMock).toHaveBeenCalledWith("case-key-1", "policy-2");
  expect(decideMock).not.toHaveBeenCalled();
});

test("a decision requires a rationale before it can be submitted", async () => {
  queueMock.mockResolvedValue({ items: [caseSummary] });
  caseDetailMock.mockResolvedValue(caseDetail);
  policiesMock.mockResolvedValue(policyList);
  render(<EntityResolutionWorkspace />);

  await waitFor(() =>
    expect(screen.getAllByText("TSMC")[0]).toBeInTheDocument(),
  );
  fireEvent.click(screen.getAllByText("TSMC")[0]);
  await waitFor(() =>
    expect(screen.getByText("Record a decision")).toBeInTheDocument(),
  );

  fireEvent.click(screen.getByRole("button", { name: "Mark unresolved" }));
  const dialog = screen.getByRole("dialog", { name: "Mark unresolved" });
  const confirmButton = within(dialog).getByRole("button", {
    name: "Confirm: Mark unresolved",
  });
  expect(confirmButton).toBeDisabled();

  fireEvent.change(within(dialog).getByLabelText("Rationale"), {
    target: { value: "Deferring for further investigation." },
  });
  expect(confirmButton).not.toBeDisabled();
  expect(decideMock).not.toHaveBeenCalled();
});

test("a successful decision submits the based_on_record_id and selected policy, then refreshes", async () => {
  queueMock.mockResolvedValue({ items: [caseSummary] });
  caseDetailMock.mockResolvedValue(caseDetail);
  policiesMock.mockResolvedValue(policyList);
  decideMock.mockResolvedValue({
    record_id: "record-2",
    understanding_key: "case-key-1",
    outcome: "Unresolved",
    business_confidence: "Low",
    produced_at: "2026-01-02T00:00:00Z",
    policy_id: "policy-1",
    policy_version: "Supplier Resolution — Conservative v1.0",
    narrative_explanation: "Unresolved using policy Conservative.",
    structured_reasons: ["Steward marked this case unresolved."],
  });
  render(<EntityResolutionWorkspace />);

  await waitFor(() =>
    expect(screen.getAllByText("TSMC")[0]).toBeInTheDocument(),
  );
  fireEvent.click(screen.getAllByText("TSMC")[0]);
  await waitFor(() =>
    expect(screen.getByText("Record a decision")).toBeInTheDocument(),
  );

  fireEvent.click(screen.getByRole("button", { name: "Mark unresolved" }));
  const decideDialog = screen.getByRole("dialog", { name: "Mark unresolved" });
  fireEvent.change(within(decideDialog).getByLabelText("Rationale"), {
    target: { value: "Deferring for further investigation." },
  });
  fireEvent.click(
    within(decideDialog).getByRole("button", {
      name: "Confirm: Mark unresolved",
    }),
  );

  await waitFor(() => expect(decideMock).toHaveBeenCalledTimes(1));
  expect(decideMock).toHaveBeenCalledWith("case-key-1", {
    action: "mark_unresolved",
    rationale: "Deferring for further investigation.",
    based_on_record_id: "record-1",
    policy_id: "policy-1",
  });
  await waitFor(() => expect(queueMock.mock.calls.length).toBeGreaterThan(1));
});

test("a stale decision (409) shows a reload prompt instead of a silent failure", async () => {
  queueMock.mockResolvedValue({ items: [caseSummary] });
  caseDetailMock.mockResolvedValue(caseDetail);
  policiesMock.mockResolvedValue(policyList);
  decideMock.mockRejectedValue(
    apiError("STALE_RESOLUTION_CASE", "Request could not be completed", 409),
  );
  render(<EntityResolutionWorkspace />);

  await waitFor(() =>
    expect(screen.getAllByText("TSMC")[0]).toBeInTheDocument(),
  );
  fireEvent.click(screen.getAllByText("TSMC")[0]);
  await waitFor(() =>
    expect(screen.getByText("Record a decision")).toBeInTheDocument(),
  );

  fireEvent.click(screen.getByRole("button", { name: "Mark unresolved" }));
  const staleDialog = screen.getByRole("dialog", { name: "Mark unresolved" });
  fireEvent.change(within(staleDialog).getByLabelText("Rationale"), {
    target: { value: "Deferring for further investigation." },
  });
  fireEvent.click(
    within(staleDialog).getByRole("button", {
      name: "Confirm: Mark unresolved",
    }),
  );

  await waitFor(() =>
    expect(
      within(staleDialog).getByText("This case has been updated"),
    ).toBeInTheDocument(),
  );
  expect(
    within(staleDialog).getByRole("button", { name: "Reload case" }),
  ).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Reload case" }));
  await waitFor(() =>
    expect(caseDetailMock.mock.calls.length).toBeGreaterThan(1),
  );
});

test("a case with no evidence profile is shown honestly, not fabricated", async () => {
  queueMock.mockResolvedValue({ items: [caseSummary] });
  caseDetailMock.mockResolvedValue({ ...caseDetail, evidence_profile: null });
  policiesMock.mockResolvedValue(policyList);
  render(<EntityResolutionWorkspace />);

  await waitFor(() =>
    expect(screen.getAllByText("TSMC")[0]).toBeInTheDocument(),
  );
  fireEvent.click(screen.getAllByText("TSMC")[0]);

  await waitFor(() =>
    expect(
      screen.getByText("No evidence profile is available"),
    ).toBeInTheDocument(),
  );
});

test("a case not found on cross-tenant access shows a bounded not-found state", async () => {
  queueMock.mockResolvedValue({ items: [caseSummary] });
  caseDetailMock.mockRejectedValue(
    apiError(
      "RESOLUTION_CASE_NOT_FOUND",
      "Request could not be completed",
      404,
    ),
  );
  policiesMock.mockResolvedValue(policyList);
  render(<EntityResolutionWorkspace />);

  await waitFor(() =>
    expect(screen.getAllByText("TSMC")[0]).toBeInTheDocument(),
  );
  fireEvent.click(screen.getAllByText("TSMC")[0]);

  await waitFor(() =>
    expect(screen.getByText("Case not found")).toBeInTheDocument(),
  );
});
