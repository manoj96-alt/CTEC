import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { AskCtecWorkspace } from "@/app/ontology-studio/ask/_components/ask-ctec-workspace";
import { OntologyCopilotApiError } from "@/lib/ontology-copilot/api-client";

const { askMock, signInMock } = vi.hoisted(() => ({
  askMock: vi.fn(),
  signInMock: vi.fn(),
}));

vi.mock("@/lib/ontology-copilot/api-client", async () => {
  const actual = await vi.importActual<
    typeof import("@/lib/ontology-copilot/api-client")
  >("@/lib/ontology-copilot/api-client");
  return {
    ...actual,
    ontologyCopilotApi: {
      ask: askMock,
    },
  };
});

vi.mock("@/lib/auth/browser-session", () => ({
  signIn: signInMock,
}));

beforeEach(() => {
  askMock.mockReset();
  signInMock.mockReset();
});

const answeredResponse = {
  status: "answered",
  intent: "products_depending_on_supplier",
  answer: "2 products depend on TSMC:\n- Product A\n- Product B",
  resolved_entity: {
    entity_id: "entity-1",
    entity_name: "TSMC",
    entity_type_name: "Supplier",
  },
  result_names: ["Product A", "Product B"],
  evidence: [
    [
      { step: 1, entity_id: "e1", entity_name: "TSMC", entity_type_name: "Supplier", relationship_name: "supplies" },
      { step: 2, entity_id: "e2", entity_name: "Material A", entity_type_name: "Material", relationship_name: "usedIn" },
      { step: 3, entity_id: "e3", entity_name: "BOM A", entity_type_name: "BOM", relationship_name: "defines" },
      { step: 4, entity_id: "e4", entity_name: "Product A", entity_type_name: "Product", relationship_name: null },
    ],
  ],
  reason: null,
};

function apiError(code: string, status = 400) {
  return new OntologyCopilotApiError(
    { code, message: "Request could not be completed", correlation_id: "corr-1", retryable: false },
    status,
  );
}

async function askQuestion(text: string) {
  fireEvent.change(screen.getByLabelText("Question"), { target: { value: text } });
  fireEvent.click(screen.getByRole("button", { name: "Ask CTEC" }));
}

test("renders the workspace with question input and submit button", () => {
  render(<AskCtecWorkspace />);
  expect(screen.getByRole("heading", { name: "Ask CTEC" })).toBeInTheDocument();
  expect(screen.getByLabelText("Question")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Ask CTEC" })).toBeInTheDocument();
});

test("submitting invokes the API with the entered question", async () => {
  askMock.mockResolvedValue(answeredResponse);
  render(<AskCtecWorkspace />);
  await askQuestion("Which products depend on TSMC?");
  await waitFor(() => expect(askMock).toHaveBeenCalledWith({ question: "Which products depend on TSMC?" }));
});

test("shows a loading state while the request is in flight", async () => {
  let resolvePromise: (value: unknown) => void = () => {};
  askMock.mockReturnValue(
    new Promise((resolve) => {
      resolvePromise = resolve;
    }),
  );
  render(<AskCtecWorkspace />);
  await askQuestion("Which products depend on TSMC?");
  expect(screen.getByRole("status")).toHaveTextContent(/Thinking/);
  resolvePromise(answeredResponse);
  await waitFor(() => expect(screen.getByRole("heading", { name: "Answer" })).toBeInTheDocument());
});

test("renders a successful answer with resolved entity and evidence", async () => {
  askMock.mockResolvedValue(answeredResponse);
  render(<AskCtecWorkspace />);
  await askQuestion("Which products depend on TSMC?");

  await waitFor(() => expect(screen.getByRole("heading", { name: "Answer" })).toBeInTheDocument());
  expect(screen.getByText(/2 products depend on TSMC/)).toBeInTheDocument();
  expect(screen.getByText(/Resolved to governed entity:/)).toBeInTheDocument();
  expect(screen.getAllByText("TSMC", { selector: "strong" }).length).toBeGreaterThan(0);
  expect(screen.getByText("Why?")).toBeInTheDocument();
  expect(screen.getByText("Product A", { selector: "strong" })).toBeInTheDocument();
  expect(screen.getByText(/supplies/)).toBeInTheDocument();
});

test("renders the unsupported-question state", async () => {
  askMock.mockResolvedValue({
    status: "unsupported_question",
    intent: null,
    answer: "This question type is not supported yet.",
    resolved_entity: null,
    result_names: [],
    evidence: [],
    reason: "UNRECOGNIZED_QUESTION",
  });
  render(<AskCtecWorkspace />);
  await askQuestion("What is the weather today?");

  await waitFor(() =>
    expect(screen.getByLabelText("Unsupported question")).toBeInTheDocument(),
  );
  expect(screen.getByText("This question type is not supported yet")).toBeInTheDocument();
});

test("renders the no-match state", async () => {
  askMock.mockResolvedValue({
    status: "no_match",
    intent: "products_depending_on_supplier",
    answer: "CTEC does not currently have sufficient governed ontology evidence to answer this question.",
    resolved_entity: null,
    result_names: [],
    evidence: [],
    reason: "NO_MATCHING_ENTITY",
  });
  render(<AskCtecWorkspace />);
  await askQuestion("Which products depend on Nobody?");

  await waitFor(() => expect(screen.getByLabelText("No match found")).toBeInTheDocument());
  expect(screen.getByText(/does not currently have sufficient governed ontology evidence/)).toBeInTheDocument();
});

test("renders the ambiguous-match state", async () => {
  askMock.mockResolvedValue({
    status: "ambiguous_match",
    intent: "products_depending_on_supplier",
    answer: "CTEC found more than one governed entity named 'TSMC' and cannot determine which one you mean.",
    resolved_entity: null,
    result_names: [],
    evidence: [],
    reason: "AMBIGUOUS_ENTITY",
  });
  render(<AskCtecWorkspace />);
  await askQuestion("Which products depend on TSMC?");

  await waitFor(() => expect(screen.getByLabelText("Ambiguous match")).toBeInTheDocument());
  expect(screen.getByText(/more than one governed entity/)).toBeInTheDocument();
});

test("renders an unauthorized state and offers sign-in", async () => {
  askMock.mockRejectedValue(apiError("AUTH_REQUIRED", 401));
  render(<AskCtecWorkspace />);
  await askQuestion("Which products depend on TSMC?");

  await waitFor(() => expect(screen.getByText("Sign in required")).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(signInMock).toHaveBeenCalledWith("/ontology-studio/ask");
});

test("renders a backend error state with a retry that re-submits the question", async () => {
  askMock.mockRejectedValueOnce(apiError("HTTP_500", 500));
  render(<AskCtecWorkspace />);
  await askQuestion("Which products depend on TSMC?");

  await waitFor(() => expect(screen.getByText("Ask CTEC service unavailable")).toBeInTheDocument());

  askMock.mockResolvedValueOnce(answeredResponse);
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await waitFor(() => expect(screen.getByRole("heading", { name: "Answer" })).toBeInTheDocument());
  expect(askMock).toHaveBeenCalledTimes(2);
});

test("network failure that is not an OntologyCopilotApiError shows a generic error", async () => {
  askMock.mockRejectedValue(new TypeError("network down"));
  render(<AskCtecWorkspace />);
  await askQuestion("Which products depend on TSMC?");

  await waitFor(() =>
    expect(screen.getByText("The Ask CTEC service could not be reached.")).toBeInTheDocument(),
  );
});
