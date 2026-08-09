import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { AssessmentForm } from "@/components/supplier-risk/assessment-form";
const { submitMock } = vi.hoisted(() => ({ submitMock: vi.fn() }));
submitMock.mockResolvedValue({ logical_execution_identifier: "logical" });
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/supplier-risk/api-client", () => ({
  supplierRiskApi: {
    submit: submitMock,
  },
}));
test("shows governed fields and accessible validation summary", () => {
  render(<AssessmentForm />);
  expect(
    screen.getByRole("heading", { name: "Assess supplier risk" }),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Submit assessment" }));
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Correct the highlighted fields",
  );
});
test("submits a complete governed form", async () => {
  render(<AssessmentForm />);
  for (const input of screen.getAllByRole("textbox"))
    fireEvent.change(input, { target: { value: crypto.randomUUID() } });
  for (const label of ["Observed at", "Effective at"])
    fireEvent.change(screen.getByLabelText(label), {
      target: { value: "2026-01-01T00:00" },
    });
  fireEvent.click(screen.getByRole("button", { name: "Submit assessment" }));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Submitting…" })).toBeDisabled(),
  );
  expect(JSON.stringify(submitMock.mock.calls[0]?.[0])).not.toContain(
    "received_at",
  );
});
