import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import Page from "@/app/quality/evidence-fitness/page";
import { EvidenceFitnessApiError } from "@/lib/evidence-fitness/api-client";
import type { ResolveResponse } from "@/lib/evidence-fitness/contracts";

const { resolveMock } = vi.hoisted(() => ({
  resolveMock: vi.fn(),
}));

vi.mock("@/lib/evidence-fitness/api-client", async () => {
  const actual = await vi.importActual<
    typeof import("@/lib/evidence-fitness/api-client")
  >("@/lib/evidence-fitness/api-client");
  return {
    ...actual,
    evidenceFitnessApi: {
      resolve: resolveMock,
    },
  };
});

beforeEach(() => {
  resolveMock.mockReset();
});

function fillAndSubmit(
  blueprintName = "Demo Blueprint",
  elementName = "Demo Element",
) {
  fireEvent.change(screen.getByLabelText(/Blueprint name/i), {
    target: { value: blueprintName },
  });
  fireEvent.change(screen.getByLabelText(/Information element name/i), {
    target: { value: elementName },
  });
  fireEvent.click(
    screen.getByRole("button", { name: /Check Evidence Fitness/i }),
  );
}

test("calls the resolve endpoint with exactly the entered blueprint/element names", async () => {
  const response: ResolveResponse = {
    information_element_requirement_id: "req-1",
    source_field_id: "field-1",
    fitness_status: "FIT",
    evaluated_at: "2026-01-01T00:00:00Z",
  };
  resolveMock.mockResolvedValueOnce(response);

  render(<Page />);
  fillAndSubmit("Supplier Risk Blueprint", "Country of Origin");

  await waitFor(() => expect(resolveMock).toHaveBeenCalledTimes(1));
  expect(resolveMock).toHaveBeenCalledWith({
    blueprint_name: "Supplier Risk Blueprint",
    information_element_name: "Country of Origin",
  });
});

test("shows a loading state while the request is in flight", async () => {
  let resolvePromise: (value: ResolveResponse) => void = () => {};
  resolveMock.mockReturnValueOnce(
    new Promise<ResolveResponse>((resolve) => {
      resolvePromise = resolve;
    }),
  );

  render(<Page />);
  fillAndSubmit();

  expect(
    await screen.findByText(/Checking evidence fitness/i),
  ).toBeInTheDocument();

  resolvePromise({
    information_element_requirement_id: "req-1",
    source_field_id: null,
    fitness_status: null,
    evaluated_at: "2026-01-01T00:00:00Z",
  });
  await waitFor(() =>
    expect(screen.getByText("Not mapped")).toBeInTheDocument(),
  );
});

test("renders UNMAPPED (source_field_id null) as a distinct, non-error, non-fabricated state", async () => {
  resolveMock.mockResolvedValueOnce({
    information_element_requirement_id: "req-1",
    source_field_id: null,
    fitness_status: null,
    evaluated_at: "2026-01-01T00:00:00Z",
  } satisfies ResolveResponse);

  render(<Page />);
  fillAndSubmit();

  expect(await screen.findByText("Not mapped")).toBeInTheDocument();
  expect(screen.getByText(/no evidence to evaluate/i)).toBeInTheDocument();
});

test("renders MAPPED/no evaluable evidence distinctly from UNMAPPED", async () => {
  resolveMock.mockResolvedValueOnce({
    information_element_requirement_id: "req-1",
    source_field_id: "field-42",
    fitness_status: null,
    evaluated_at: "2026-01-01T00:00:00Z",
  } satisfies ResolveResponse);

  render(<Page />);
  fillAndSubmit();

  expect(
    await screen.findByText("Mapped, no evaluable evidence"),
  ).toBeInTheDocument();
  expect(screen.queryByText("Not mapped")).not.toBeInTheDocument();
});

test("renders FIT exactly as returned by the API, never fabricated", async () => {
  resolveMock.mockResolvedValueOnce({
    information_element_requirement_id: "req-1",
    source_field_id: "field-1",
    fitness_status: "FIT",
    evaluated_at: "2026-01-01T00:00:00Z",
  } satisfies ResolveResponse);

  render(<Page />);
  fillAndSubmit();

  expect(await screen.findByText("FIT")).toBeInTheDocument();
});

test("renders STALE exactly as returned by the API", async () => {
  resolveMock.mockResolvedValueOnce({
    information_element_requirement_id: "req-1",
    source_field_id: "field-1",
    fitness_status: "STALE",
    evaluated_at: "2026-01-01T00:00:00Z",
  } satisfies ResolveResponse);

  render(<Page />);
  fillAndSubmit();

  expect(await screen.findByText("STALE")).toBeInTheDocument();
});

test("renders CONFLICTING exactly as returned by the API", async () => {
  resolveMock.mockResolvedValueOnce({
    information_element_requirement_id: "req-1",
    source_field_id: "field-1",
    fitness_status: "CONFLICTING",
    evaluated_at: "2026-01-01T00:00:00Z",
  } satisfies ResolveResponse);

  render(<Page />);
  fillAndSubmit();

  expect(await screen.findByText("CONFLICTING")).toBeInTheDocument();
});

test("a 401 renders an honest not-authorized state", async () => {
  resolveMock.mockRejectedValueOnce(
    new EvidenceFitnessApiError("AUTH_REQUIRED", 401),
  );

  render(<Page />);
  fillAndSubmit();

  expect(await screen.findByText("Not authorized")).toBeInTheDocument();
});

test("a 403 renders an honest not-authorized state", async () => {
  resolveMock.mockRejectedValueOnce(
    new EvidenceFitnessApiError("AUTHORIZATION_SCOPE_REQUIRED", 403),
  );

  render(<Page />);
  fillAndSubmit();

  expect(await screen.findByText("Not authorized")).toBeInTheDocument();
});

test("a 404 renders an honest not-found state", async () => {
  resolveMock.mockRejectedValueOnce(
    new EvidenceFitnessApiError("BLUEPRINT_NOT_FOUND", 404),
  );

  render(<Page />);
  fillAndSubmit();

  expect(await screen.findByText("Not found")).toBeInTheDocument();
  expect(
    screen.getByText(/No governed blueprint matches that name/i),
  ).toBeInTheDocument();
});

test("a 422 renders an honest validation/ambiguous-name state", async () => {
  resolveMock.mockRejectedValueOnce(
    new EvidenceFitnessApiError("INFORMATION_ELEMENT_NAME_AMBIGUOUS", 422),
  );

  render(<Page />);
  fillAndSubmit();

  expect(
    await screen.findByText("Request could not be resolved"),
  ).toBeInTheDocument();
});

test("a 500/server failure renders an honest failure state, never a fabricated result", async () => {
  resolveMock.mockRejectedValueOnce(
    new EvidenceFitnessApiError("SERVER_ERROR", 500),
  );

  render(<Page />);
  fillAndSubmit();

  expect(
    await screen.findByText("Evidence Fitness could not be checked"),
  ).toBeInTheDocument();
  // "Governed result" only renders for state.status === "result" -- its
  // absence here proves no fitness value was fabricated from the failure.
  expect(screen.queryByText("Governed result")).not.toBeInTheDocument();
});

test("a network failure (non-ApiError throw) renders an honest failure state", async () => {
  resolveMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));

  render(<Page />);
  fillAndSubmit();

  expect(
    await screen.findByText("Evidence Fitness could not be checked"),
  ).toBeInTheDocument();
});

test("the page never claims generalized Data Quality or Simulation coupling", () => {
  render(<Page />);
  expect(
    screen.getByText(/is not part of, and does not imply/i),
  ).toBeInTheDocument();
  expect(screen.queryByText(/[Ss]imulation/)).not.toBeInTheDocument();
});
