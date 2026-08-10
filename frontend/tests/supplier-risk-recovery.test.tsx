import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, vi } from "vitest";
import { RetryDialog } from "@/components/supplier-risk/retry-dialog";
import { ReplayDialog } from "@/components/supplier-risk/replay-dialog";
const { replayMock } = vi.hoisted(() => ({ replayMock: vi.fn() }));
vi.mock("@/lib/supplier-risk/api-client", () => ({
  supplierRiskApi: {
    retry: vi.fn().mockResolvedValue({}),
    replay: replayMock,
  },
}));
const replayOption = (option_reference: string, stage_label = "ERM") => ({
  option_reference,
  source_attempt_identifier: "attempt",
  stage_label,
  checkpoint_at: "2026-01-01T00:00:00Z",
  eligible: true,
  reason_code: "REPLAY_ELIGIBLE",
  revision: 2,
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
  replayMock.mockReset();
  replayMock.mockResolvedValue({});
});
test("retry is server eligibility controlled", () => {
  render(
    <RetryDialog
      logicalId="logical"
      eligibility={{
        eligible: false,
        governing_attempt_identifier: "attempt",
        reason_code: "ATTEMPT_NOT_FAILED",
        safe_constraint: null,
        revision: 1,
        action: null,
      }}
      onAccepted={vi.fn()}
    />,
  );
  expect(screen.getByRole("button", { name: "Request retry" })).toBeDisabled();
});
test("eligible retry submits one revision-bound request", async () => {
  const accepted = vi.fn();
  render(
    <RetryDialog
      logicalId="logical"
      eligibility={{
        eligible: true,
        governing_attempt_identifier: "attempt",
        reason_code: "RETRY_ELIGIBLE",
        safe_constraint: null,
        revision: 3,
        action: "/retry",
      }}
      onAccepted={accepted}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Request retry" }));
  fireEvent.change(screen.getByLabelText("Reason"), {
    target: { value: "Evidence corrected" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Confirm retry" }));
  await waitFor(() => expect(accepted).toHaveBeenCalled());
});
test("replay displays only server-authorized options", async () => {
  render(
    <ReplayDialog
      logicalId="logical"
      options={[
        {
          option_reference: "option",
          source_attempt_identifier: "attempt",
          stage_label: "ERM",
          checkpoint_at: "2026-01-01T00:00:00Z",
          eligible: true,
          reason_code: "REPLAY_ELIGIBLE",
          revision: 2,
        },
      ]}
      onAccepted={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Privileged replay" }));
  await waitFor(() =>
    expect(screen.getByLabelText("Server-authorized checkpoint")).toHaveValue(
      "option",
    ),
  );
  expect(screen.getByLabelText("Server-authorized checkpoint")).toHaveValue(
    "option",
  );
  expect(screen.getByText(/will not be overwritten/)).toBeInTheDocument();
});
test("confirmed replay submits only the server option", async () => {
  const accepted = vi.fn();
  render(
    <ReplayDialog
      logicalId="logical"
      options={[
        {
          option_reference: "option",
          source_attempt_identifier: "attempt",
          stage_label: "ERM",
          checkpoint_at: "2026-01-01T00:00:00Z",
          eligible: true,
          reason_code: "REPLAY_ELIGIBLE",
          revision: 2,
        },
      ]}
      onAccepted={accepted}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Privileged replay" }));
  fireEvent.change(screen.getByLabelText("Reason"), {
    target: { value: "Authorized recovery" },
  });
  const confirm = screen.getByRole("button", {
    name: "Confirm privileged replay",
  });
  await waitFor(() => expect(confirm).not.toBeDisabled());
  fireEvent.click(confirm);
  await waitFor(() => expect(accepted).toHaveBeenCalled());
  expect(replayMock).toHaveBeenCalledTimes(1);
  expect(replayMock.mock.calls[0]?.[1]).toMatchObject({
    replay_option_reference: "option",
    expected_revision: 2,
  });
});

test("submits the visibly selected alternative option", async () => {
  render(
    <ReplayDialog
      logicalId="logical"
      options={[replayOption("first"), replayOption("second", "GRM")]}
      onAccepted={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Privileged replay" }));
  await waitFor(() =>
    expect(screen.getByLabelText("Server-authorized checkpoint")).toHaveValue(
      "first",
    ),
  );
  fireEvent.change(screen.getByLabelText("Server-authorized checkpoint"), {
    target: { value: "second" },
  });
  fireEvent.change(screen.getByLabelText("Reason"), {
    target: { value: "Authorized recovery" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Confirm privileged replay" }),
  );
  await waitFor(() => expect(replayMock).toHaveBeenCalledTimes(1));
  expect(replayMock.mock.calls[0]?.[1]).toMatchObject({
    replay_option_reference: "second",
  });
});

test("pending confirmation emits only one replay request", async () => {
  let resolveReplay!: (value: object) => void;
  replayMock.mockReturnValue(
    new Promise((resolve) => {
      resolveReplay = resolve;
    }),
  );
  render(
    <ReplayDialog
      logicalId="logical"
      options={[replayOption("option")]}
      onAccepted={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Privileged replay" }));
  await waitFor(() =>
    expect(screen.getByLabelText("Server-authorized checkpoint")).toHaveValue(
      "option",
    ),
  );
  fireEvent.change(screen.getByLabelText("Reason"), {
    target: { value: "Authorized recovery" },
  });
  const confirm = screen.getByRole("button", {
    name: "Confirm privileged replay",
  });
  fireEvent.click(confirm);
  fireEvent.click(confirm);
  expect(replayMock).toHaveBeenCalledTimes(1);
  resolveReplay({});
  await waitFor(() => expect(confirm).not.toBeDisabled());
});
