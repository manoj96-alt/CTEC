import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

// CDD-045 companion (OQI-UX lifecycle closure + authorization-ID contract
// correction): the new governed-action interaction boundary. Proves the
// exact frozen contract -- decided_by sourced from the authenticated
// principal only, never free text; the real authorization_id (never a
// placeholder) drives both action calls; every domain error is surfaced
// honestly and distinctly; every successful mutation triggers a full
// server refresh, never an optimistic lifecycle patch; the 8-state
// case_status stepper (including the rejected composite rule) renders
// exactly the frozen mapping; and the whole panel continues to prove
// recommendation != authorization != remediation != resolution.
const {
  decideAuthorizationMock,
  reportExecutionMock,
  prepareRemediationMock,
  principalIdMock,
} = vi.hoisted(() => ({
  decideAuthorizationMock: vi.fn(),
  reportExecutionMock: vi.fn(),
  prepareRemediationMock: vi.fn(),
  principalIdMock: vi.fn(),
}));

vi.mock("@/lib/oqi/api-client", () => ({
  oqiApi: {
    decideAuthorization: decideAuthorizationMock,
    reportExecution: reportExecutionMock,
    prepareRemediation: prepareRemediationMock,
  },
  OqiApiError: class OqiApiError extends Error {
    constructor(
      public code: string,
      public status: number,
    ) {
      super(code);
    }
  },
}));

vi.mock("@/lib/auth/browser-session", () => ({
  principalId: principalIdMock,
}));

import { OqiApiError } from "@/lib/oqi/api-client";
import { DecideAuthorizationDialog } from "@/app/quality/findings/[findingId]/_components/decide-authorization-dialog";
import { ReportExecutionDialog } from "@/app/quality/findings/[findingId]/_components/report-execution-dialog";
import { RemediationStepper } from "@/app/quality/findings/[findingId]/_components/remediation-stepper";
import { RemediationPanel } from "@/app/quality/findings/[findingId]/_components/remediation-panel";
import type { RemediationResponse } from "@/lib/oqi/contracts";

beforeAll(() => {
  // jsdom's native <dialog> support is unreliable across versions --
  // mirrors this repository's own existing entity-resolution decision
  // dialog test precedent exactly.
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
});

beforeEach(() => {
  decideAuthorizationMock.mockReset();
  reportExecutionMock.mockReset();
  prepareRemediationMock.mockReset();
  principalIdMock.mockReset();
  principalIdMock.mockResolvedValue("sub-authenticated-principal");
});

describe("Decide Authorization Dialog — authenticated identity", () => {
  it("decided_by is sourced from the authenticated sub claim, never free text", async () => {
    decideAuthorizationMock.mockResolvedValue({ case_status: "AUTHORIZED" });
    render(
      <DecideAuthorizationDialog
        authorizationId="11111111-1111-1111-1111-111111111111"
        instruction="UPDATE_FIELD"
        onDecided={() => {}}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Decide Authorization" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Confirm: Approve" }));

    await waitFor(() => expect(decideAuthorizationMock).toHaveBeenCalled());
    expect(decideAuthorizationMock).toHaveBeenCalledWith(
      "11111111-1111-1111-1111-111111111111",
      {
        approve: true,
        decided_by: "sub-authenticated-principal",
        rejection_reason: undefined,
      },
    );
  });

  it("decided_by is never rendered as an editable form field", () => {
    render(
      <DecideAuthorizationDialog
        authorizationId="auth-1"
        instruction="x"
        onDecided={() => {}}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Decide Authorization" }),
    );
    expect(screen.queryByLabelText(/decided.?by/i)).not.toBeInTheDocument();
    expect(
      screen.queryByDisplayValue("sub-authenticated-principal"),
    ).not.toBeInTheDocument();
  });

  it("missing sub fails closed -- no decide call is made", async () => {
    principalIdMock.mockResolvedValue(null);
    render(
      <DecideAuthorizationDialog
        authorizationId="auth-1"
        instruction="x"
        onDecided={() => {}}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Decide Authorization" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Confirm: Approve" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/authenticated principal/i);
    expect(decideAuthorizationMock).not.toHaveBeenCalled();
  });
});

describe("Decide Authorization Dialog — approval and rejection", () => {
  it("Approve sends approve=true with the real authorization_id", async () => {
    decideAuthorizationMock.mockResolvedValue({ case_status: "AUTHORIZED" });
    const onDecided = vi.fn();
    render(
      <DecideAuthorizationDialog
        authorizationId="real-auth-id-abc"
        instruction="x"
        onDecided={onDecided}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Decide Authorization" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Confirm: Approve" }));
    await waitFor(() => expect(onDecided).toHaveBeenCalled());
    expect(decideAuthorizationMock.mock.calls[0][0]).toBe("real-auth-id-abc");
    expect(decideAuthorizationMock.mock.calls[0][1].approve).toBe(true);
  });

  it("Reject sends approve=false with the supplied rejection_reason", async () => {
    decideAuthorizationMock.mockResolvedValue({
      case_status: "AWAITING_AUTHORITY",
    });
    render(
      <DecideAuthorizationDialog
        authorizationId="auth-1"
        instruction="x"
        onDecided={() => {}}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Decide Authorization" }),
    );
    fireEvent.click(screen.getByRole("radio", { name: "Reject" }));
    fireEvent.change(screen.getByLabelText(/rejection reason/i), {
      target: { value: "Instruction targets the wrong field." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Confirm: Reject" }));

    await waitFor(() => expect(decideAuthorizationMock).toHaveBeenCalled());
    expect(decideAuthorizationMock).toHaveBeenCalledWith("auth-1", {
      approve: false,
      decided_by: "sub-authenticated-principal",
      rejection_reason: "Instruction targets the wrong field.",
    });
  });

  it("a successful decision triggers the caller's refresh callback", async () => {
    decideAuthorizationMock.mockResolvedValue({ case_status: "AUTHORIZED" });
    const onDecided = vi.fn();
    render(
      <DecideAuthorizationDialog
        authorizationId="auth-1"
        instruction="x"
        onDecided={onDecided}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Decide Authorization" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Confirm: Approve" }));
    await waitFor(() => expect(onDecided).toHaveBeenCalledTimes(1));
  });
});

describe("Decide Authorization Dialog — domain errors", () => {
  it("self-approval prohibition is shown distinctly, not generically", async () => {
    decideAuthorizationMock.mockRejectedValue(
      new OqiApiError("REMEDIATION_SELF_APPROVAL_PROHIBITED", 403),
    );
    render(
      <DecideAuthorizationDialog
        authorizationId="auth-1"
        instruction="x"
        onDecided={() => {}}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Decide Authorization" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Confirm: Approve" }));
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/requested this authorization/i);
  });

  it("not-pending is shown distinctly, not generically", async () => {
    decideAuthorizationMock.mockRejectedValue(
      new OqiApiError("REMEDIATION_AUTHORIZATION_NOT_PENDING", 409),
    );
    render(
      <DecideAuthorizationDialog
        authorizationId="auth-1"
        instruction="x"
        onDecided={() => {}}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Decide Authorization" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Confirm: Approve" }));
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/no longer pending/i);
  });
});

describe("Report Execution Dialog", () => {
  it("sends no invented fields -- exactly the real authorization_id, no body", async () => {
    reportExecutionMock.mockResolvedValue({
      case_status: "EXTERNAL_EXECUTION_REPORTED",
    });
    render(
      <ReportExecutionDialog
        authorizationId="real-auth-id-xyz"
        onReported={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Report Execution" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Confirm: Report Execution" }),
    );
    await waitFor(() => expect(reportExecutionMock).toHaveBeenCalled());
    expect(reportExecutionMock).toHaveBeenCalledWith("real-auth-id-xyz");
    expect(reportExecutionMock.mock.calls[0]).toHaveLength(1);
  });

  it("a successful report triggers the caller's refresh callback", async () => {
    reportExecutionMock.mockResolvedValue({
      case_status: "EXTERNAL_EXECUTION_REPORTED",
    });
    const onReported = vi.fn();
    render(
      <ReportExecutionDialog
        authorizationId="auth-1"
        onReported={onReported}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Report Execution" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Confirm: Report Execution" }),
    );
    await waitFor(() => expect(onReported).toHaveBeenCalledTimes(1));
  });

  it("action-mismatch (staleness) is shown distinctly, not generically", async () => {
    reportExecutionMock.mockRejectedValue(
      new OqiApiError("REMEDIATION_ACTION_MISMATCH", 409),
    );
    render(
      <ReportExecutionDialog authorizationId="auth-1" onReported={() => {}} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Report Execution" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Confirm: Report Execution" }),
    );
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(
      /changed since this remediation was authorized/i,
    );
  });

  it("already-consumed is shown distinctly, not generically", async () => {
    reportExecutionMock.mockRejectedValue(
      new OqiApiError("REMEDIATION_AUTHORIZATION_ALREADY_CONSUMED", 409),
    );
    render(
      <ReportExecutionDialog authorizationId="auth-1" onReported={() => {}} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Report Execution" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Confirm: Report Execution" }),
    );
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/already been reported/i);
  });

  it("never implies CTEC writes to the source system", () => {
    render(
      <ReportExecutionDialog authorizationId="auth-1" onReported={() => {}} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Report Execution" }));
    expect(
      screen.getByText(/does not write to the source system/i),
    ).toBeInTheDocument();
  });

  it("never implies the Finding is resolved", () => {
    render(
      <ReportExecutionDialog authorizationId="auth-1" onReported={() => {}} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Report Execution" }));
    expect(
      screen.getByText(/does not resolve the finding/i),
    ).toBeInTheDocument();
  });
});

describe("Remediation Stepper — exact 8-state mapping", () => {
  const linearCases: [string, string][] = [
    ["CANDIDATE_READY", "Candidate Ready"],
    ["AWAITING_AUTHORITY", "Awaiting Human Authorization"],
    ["AUTHORIZED", "Authorized"],
    ["EXTERNAL_EXECUTION_REPORTED", "Externally Reported"],
    ["AWAITING_REEVALUATION", "Awaiting Re-evaluation"],
    ["RESOLVED", "Resolved"],
  ];

  it.each(linearCases)(
    "case_status %s renders the linear step %s",
    (caseStatus, label) => {
      const remediation = {
        case_status: caseStatus,
        candidates: [],
        recommendation: null,
        external_execution: null,
      } as unknown as RemediationResponse;
      render(<RemediationStepper remediation={remediation} />);
      const group = screen.getByRole("group", {
        name: "Remediation lifecycle",
      });
      expect(group.textContent).toContain(label);
    },
  );

  it("STEWARD_INVESTIGATION renders as a side state, not a linear step", () => {
    const remediation = {
      case_status: "STEWARD_INVESTIGATION",
      candidates: [],
      recommendation: null,
      external_execution: null,
    } as unknown as RemediationResponse;
    render(<RemediationStepper remediation={remediation} />);
    expect(screen.getByText("Steward Investigation")).toBeInTheDocument();
    expect(screen.queryByText("Candidate Ready")).not.toBeInTheDocument();
  });

  it("NO_REMEDIATION renders as a side state, not a linear step", () => {
    const remediation = {
      case_status: "NO_REMEDIATION",
      candidates: [],
      recommendation: null,
      external_execution: null,
    } as unknown as RemediationResponse;
    render(<RemediationStepper remediation={remediation} />);
    expect(screen.getByText("No Remediation")).toBeInTheDocument();
  });

  it("rejected composite: AWAITING_AUTHORITY + every candidate REJECTED renders Rejected, never Awaiting Human Authorization", () => {
    const remediation = {
      case_status: "AWAITING_AUTHORITY",
      candidates: [
        {
          candidate_id: "c1",
          proposed_value: "ABC123",
          basis: "SPECIALIST_SUPPORTED",
          authorization: {
            authorization_id: "auth-1",
            status: "REJECTED",
            requested_by: "agent",
            requested_on: "2025-12-31T00:00:00Z",
            decided_by: "requester",
            decided_on: "2026-01-01T00:00:00Z",
            rejection_reason: "wrong field",
            is_stale: false,
          },
        },
      ],
      recommendation: null,
      external_execution: null,
    } as unknown as RemediationResponse;
    render(<RemediationStepper remediation={remediation} />);
    expect(screen.getByText("Rejected")).toBeInTheDocument();
    expect(
      screen.queryByText("Awaiting Human Authorization"),
    ).not.toBeInTheDocument();
  });

  it("AWAITING_AUTHORITY without a rejected authorization still renders the ordinary linear step", () => {
    const remediation = {
      case_status: "AWAITING_AUTHORITY",
      candidates: [
        {
          candidate_id: "c1",
          proposed_value: "ABC123",
          basis: "SPECIALIST_SUPPORTED",
          authorization: {
            authorization_id: "auth-1",
            status: "PENDING",
            requested_by: "agent",
            requested_on: "2026-01-01T00:00:00Z",
            decided_by: null,
            decided_on: null,
            rejection_reason: null,
            is_stale: false,
          },
        },
      ],
      recommendation: null,
      external_execution: null,
    } as unknown as RemediationResponse;
    render(<RemediationStepper remediation={remediation} />);
    expect(
      screen.getByText(/Awaiting Human Authorization/),
    ).toBeInTheDocument();
    expect(screen.queryByText("Rejected")).not.toBeInTheDocument();
  });

  it("renders nothing when no case exists yet (case_status null)", () => {
    const remediation = {
      case_status: null,
      candidates: [],
      recommendation: null,
      external_execution: null,
    } as unknown as RemediationResponse;
    const { container } = render(
      <RemediationStepper remediation={remediation} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("CDD-062: current step carries aria-current=step and a distinct, non-color class from past/future steps", () => {
    const remediation = {
      case_status: "AUTHORIZED",
      candidates: [],
      recommendation: null,
      external_execution: null,
    } as unknown as RemediationResponse;
    render(<RemediationStepper remediation={remediation} />);

    const current = screen.getByText("Authorized").closest("li");
    const past = screen.getByText("Candidate Ready").closest("li");
    const future = screen.getByText("Resolved").closest("li");

    expect(current).toHaveAttribute("aria-current", "step");
    expect(current).toHaveClass("stepper-step--current");
    expect(past).toHaveClass("stepper-step--past");
    expect(past).not.toHaveAttribute("aria-current");
    expect(future).toHaveClass("stepper-step--future");
    expect(future).not.toHaveAttribute("aria-current");
    // Each step carries a decorative, non-color marker distinct from its
    // label text -- the class distinction above, not color alone, is what
    // this test proves.
    expect(current?.querySelector(".stepper-marker")).not.toBeNull();
  });

  it("CDD-081 §13: the awaiting-authority marker class applies only to the live AWAITING_AUTHORITY current step, not to any other step", () => {
    const remediation = {
      case_status: "AWAITING_AUTHORITY",
      candidates: [],
      recommendation: null,
      external_execution: null,
    } as unknown as RemediationResponse;
    render(<RemediationStepper remediation={remediation} />);

    const current = screen
      .getByText("Awaiting Human Authorization")
      .closest("li");
    expect(current).toHaveClass("stepper-step--awaiting-authority");

    const other = screen.getByText("Candidate Ready").closest("li");
    expect(other).not.toHaveClass("stepper-step--awaiting-authority");
  });

  it("CDD-081 §13: a past rendering of the Awaiting Human Authorization step never carries the awaiting-authority marker", () => {
    const remediation = {
      case_status: "AUTHORIZED",
      candidates: [],
      recommendation: null,
      external_execution: null,
    } as unknown as RemediationResponse;
    render(<RemediationStepper remediation={remediation} />);

    const pastAwaitingAuthority = screen
      .getByText("Awaiting Human Authorization")
      .closest("li");
    expect(pastAwaitingAuthority).toHaveClass("stepper-step--past");
    expect(pastAwaitingAuthority).not.toHaveClass(
      "stepper-step--awaiting-authority",
    );
  });

  it("CDD-062: rejected composite renders as its own group, never inside the linear <ol> step list", () => {
    const remediation = {
      case_status: "AWAITING_AUTHORITY",
      candidates: [
        {
          candidate_id: "c1",
          proposed_value: "ABC123",
          basis: "SPECIALIST_SUPPORTED",
          authorization: {
            authorization_id: "auth-1",
            status: "REJECTED",
            requested_by: "agent",
            requested_on: "2025-12-31T00:00:00Z",
            decided_by: "requester",
            decided_on: "2026-01-01T00:00:00Z",
            rejection_reason: "wrong field",
            is_stale: false,
          },
        },
      ],
      recommendation: null,
      external_execution: null,
    } as unknown as RemediationResponse;
    render(<RemediationStepper remediation={remediation} />);
    expect(screen.getByText("Rejected")).toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  // CDD-085 G-R3/G-R4/G-R5: the multi-candidate rejection matrix -- overall
  // Rejected requires EVERY candidate to be explicitly REJECTED. A mixed
  // REJECTED+PENDING case is genuinely still awaiting a human decision on
  // the sibling; an APPROVED+SUPERSEDED case genuinely succeeded (the
  // supersession is a system-caused consequence of approval, never a
  // rejection) -- neither may ever collapse to the Rejected composite.
  it("REJECTED + PENDING siblings: not overall Rejected, still Awaiting Human Authorization", () => {
    const remediation = {
      case_status: "AWAITING_AUTHORITY",
      candidates: [
        {
          candidate_id: "c1",
          proposed_value: "US",
          basis: "SPECIALIST_SUPPORTED",
          authorization: {
            authorization_id: "auth-1",
            status: "REJECTED",
            requested_by: "agent",
            requested_on: "2025-12-31T00:00:00Z",
            decided_by: "requester",
            decided_on: "2026-01-01T00:00:00Z",
            rejection_reason: "wrong field",
            is_stale: false,
          },
        },
        {
          candidate_id: "c2",
          proposed_value: "MX",
          basis: "SPECIALIST_SUPPORTED",
          authorization: {
            authorization_id: "auth-2",
            status: "PENDING",
            requested_by: "agent",
            requested_on: "2026-01-01T00:00:00Z",
            decided_by: null,
            decided_on: null,
            rejection_reason: null,
            is_stale: false,
          },
        },
      ],
      recommendation: null,
      external_execution: null,
    } as unknown as RemediationResponse;
    render(<RemediationStepper remediation={remediation} />);
    expect(screen.queryByText("Rejected")).not.toBeInTheDocument();
    expect(
      screen.getByText(/Awaiting Human Authorization/),
    ).toBeInTheDocument();
  });

  it("APPROVED + SUPERSEDED siblings: Authorized, never Rejected", () => {
    const remediation = {
      case_status: "AUTHORIZED",
      candidates: [
        {
          candidate_id: "c1",
          proposed_value: "US",
          basis: "SPECIALIST_SUPPORTED",
          authorization: {
            authorization_id: "auth-1",
            status: "APPROVED",
            requested_by: "agent",
            requested_on: "2025-12-31T00:00:00Z",
            decided_by: "steward@example.com",
            decided_on: "2026-01-01T00:00:00Z",
            rejection_reason: null,
            is_stale: false,
          },
        },
        {
          candidate_id: "c2",
          proposed_value: "MX",
          basis: "SPECIALIST_SUPPORTED",
          authorization: {
            authorization_id: "auth-2",
            status: "SUPERSEDED",
            requested_by: "agent",
            requested_on: "2025-12-31T00:00:00Z",
            decided_by: null,
            decided_on: null,
            rejection_reason: null,
            is_stale: false,
          },
        },
      ],
      recommendation: null,
      external_execution: null,
    } as unknown as RemediationResponse;
    render(<RemediationStepper remediation={remediation} />);
    expect(screen.queryByText("Rejected")).not.toBeInTheDocument();
    const current = screen.getByText("Authorized").closest("li");
    expect(current).toHaveAttribute("aria-current", "step");
  });
});

describe("Remediation Panel — governed truth boundary", () => {
  const FULL_REMEDIATION: RemediationResponse = {
    case_status: "AWAITING_AUTHORITY",
    candidates: [
      {
        candidate_id: "candidate-1",
        proposed_value: "ABC123",
        basis: "SPECIALIST_SUPPORTED",
        authorization: {
          authorization_id: "auth-real-id",
          status: "PENDING",
          requested_by: "agent",
          requested_on: "2026-01-01T00:00:00Z",
          decided_by: null,
          decided_on: null,
          rejection_reason: null,
          is_stale: false,
        },
      },
    ],
    recommendation: {
      recommendation_type: "RECOMMEND_CANDIDATE",
      candidate_id: "candidate-1",
      rationale: "Majority of governed peers agree.",
      basis: "SPECIALIST_SUPPORTED",
    },
    external_execution: null,
  };

  it("recommendation and authorization remain two visually distinct blocks", () => {
    render(
      <RemediationPanel
        remediation={FULL_REMEDIATION}
        findingId="f1"
        onMutated={() => {}}
      />,
    );
    expect(screen.getByText("Agent Recommendation")).toBeInTheDocument();
    // "Human Authorization" appears both as the panel's section eyebrow and
    // as the (closed) dialog's own title -- both are legitimate, distinct
    // occurrences of the same governed label, not a duplication defect.
    expect(
      screen.getAllByText("Human Authorization").length,
    ).toBeGreaterThanOrEqual(1);
    expect(
      screen.getByText("Authorization pending decision"),
    ).toBeInTheDocument();
  });

  it("a PENDING authorization exposes the decide action using the real authorization_id", async () => {
    decideAuthorizationMock.mockResolvedValue({ case_status: "AUTHORIZED" });
    render(
      <RemediationPanel
        remediation={FULL_REMEDIATION}
        findingId="f1"
        onMutated={() => {}}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Decide Authorization" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Confirm: Approve" }));
    await waitFor(() => expect(decideAuthorizationMock).toHaveBeenCalled());
    expect(decideAuthorizationMock.mock.calls[0][0]).toBe("auth-real-id");
  });

  it("an APPROVED, not-yet-reported authorization exposes report-execution using the real authorization_id", async () => {
    reportExecutionMock.mockResolvedValue({
      case_status: "EXTERNAL_EXECUTION_REPORTED",
    });
    const approved: RemediationResponse = {
      ...FULL_REMEDIATION,
      case_status: "AUTHORIZED",
      candidates: [
        {
          ...FULL_REMEDIATION.candidates[0],
          authorization: {
            ...FULL_REMEDIATION.candidates[0].authorization!,
            status: "APPROVED",
            decided_by: "steward@example.com",
            decided_on: "2026-01-01T00:00:00Z",
          },
        },
      ],
    };
    render(
      <RemediationPanel
        remediation={approved}
        findingId="f1"
        onMutated={() => {}}
      />,
    );
    expect(
      screen.queryByRole("button", { name: "Decide Authorization" }),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Report Execution" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Confirm: Report Execution" }),
    );
    await waitFor(() => expect(reportExecutionMock).toHaveBeenCalled());
    expect(reportExecutionMock).toHaveBeenCalledWith("auth-real-id");
  });

  it("a successful decision refreshes via the parent's onMutated, not an optimistic local patch", async () => {
    decideAuthorizationMock.mockResolvedValue({ case_status: "AUTHORIZED" });
    const onMutated = vi.fn();
    render(
      <RemediationPanel
        remediation={FULL_REMEDIATION}
        findingId="f1"
        onMutated={onMutated}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Decide Authorization" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Confirm: Approve" }));
    await waitFor(() => expect(onMutated).toHaveBeenCalledTimes(1));
    // The rendered panel is still driven by the original, unmutated prop --
    // proving no client-side lifecycle state was invented locally.
    expect(
      screen.getByText("Authorization pending decision"),
    ).toBeInTheDocument();
  });

  it("external execution reported never says Resolved -- awaiting fresh evidence instead", () => {
    const reported: RemediationResponse = {
      ...FULL_REMEDIATION,
      case_status: "EXTERNAL_EXECUTION_REPORTED",
      candidates: [
        {
          ...FULL_REMEDIATION.candidates[0],
          authorization: {
            ...FULL_REMEDIATION.candidates[0].authorization!,
            status: "APPROVED",
            decided_by: "steward@example.com",
            decided_on: "2026-01-01T00:00:00Z",
          },
        },
      ],
      external_execution: { reported_at: "2026-01-02T00:00:00Z" },
    };
    render(
      <RemediationPanel
        remediation={reported}
        findingId="f1"
        onMutated={() => {}}
      />,
    );
    expect(
      screen.getByText(
        /External remediation reported — awaiting fresh evidence/,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /does not by itself resolve the underlying quality condition/i,
      ),
    ).toBeInTheDocument();
    // The stepper legitimately lists "Resolved" as a future roadmap step --
    // the honesty requirement is that it is never the CURRENT step.
    expect(
      screen.getByRole("listitem", { current: "step" }).textContent,
    ).not.toMatch(/^Resolved/);
    // Already reported -- report-execution is no longer offered.
    expect(
      screen.queryByRole("button", { name: "Report Execution" }),
    ).not.toBeInTheDocument();
  });

  it("candidate remains labeled not-established-truth even alongside a decided authorization", () => {
    const decided: RemediationResponse = {
      ...FULL_REMEDIATION,
      candidates: [
        {
          ...FULL_REMEDIATION.candidates[0],
          authorization: {
            ...FULL_REMEDIATION.candidates[0].authorization!,
            status: "APPROVED",
            decided_by: "steward@example.com",
            decided_on: "2026-01-01T00:00:00Z",
          },
        },
      ],
    };
    render(
      <RemediationPanel
        remediation={decided}
        findingId="f1"
        onMutated={() => {}}
      />,
    );
    expect(
      screen.getByText("Candidate — not established truth"),
    ).toBeInTheDocument();
  });

  it("empty state offers Prepare remediation; clicking it triggers the caller's refresh callback", async () => {
    prepareRemediationMock.mockResolvedValue({
      case_status: "CANDIDATE_READY",
    });
    const onMutated = vi.fn();
    const empty: RemediationResponse = {
      case_status: null,
      candidates: [],
      recommendation: null,
      external_execution: null,
    };
    render(
      <RemediationPanel
        remediation={empty}
        findingId="f1"
        onMutated={onMutated}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Prepare remediation" }),
    );
    await waitFor(() => expect(onMutated).toHaveBeenCalledTimes(1));
    expect(prepareRemediationMock).toHaveBeenCalledWith("f1");
  });

  it("a SUPERSEDED candidate exposes no decide or execute action", () => {
    const withSuperseded: RemediationResponse = {
      ...FULL_REMEDIATION,
      case_status: "AUTHORIZED",
      candidates: [
        {
          candidate_id: "candidate-2",
          proposed_value: "MX",
          basis: "SPECIALIST_SUPPORTED",
          authorization: {
            authorization_id: "auth-superseded",
            status: "SUPERSEDED",
            requested_by: "agent",
            requested_on: "2026-01-01T00:00:00Z",
            decided_by: null,
            decided_on: null,
            rejection_reason: null,
            is_stale: false,
          },
        },
      ],
    };
    render(
      <RemediationPanel
        remediation={withSuperseded}
        findingId="f1"
        onMutated={() => {}}
      />,
    );
    expect(
      screen.getByText("Superseded — an alternative candidate was approved"),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Decide Authorization" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Report Execution" }),
    ).not.toBeInTheDocument();
  });

  it("once external execution is reported, no candidate -- including a still-APPROVED one -- exposes Report Execution again", () => {
    const approvedButAlreadyReported: RemediationResponse = {
      case_status: "EXTERNAL_EXECUTION_REPORTED",
      candidates: [
        {
          candidate_id: "candidate-1",
          proposed_value: "US",
          basis: "SPECIALIST_SUPPORTED",
          authorization: {
            authorization_id: "auth-1",
            status: "APPROVED",
            requested_by: "agent",
            requested_on: "2025-12-31T00:00:00Z",
            decided_by: "steward@example.com",
            decided_on: "2026-01-01T00:00:00Z",
            rejection_reason: null,
            is_stale: false,
          },
        },
      ],
      recommendation: null,
      external_execution: { reported_at: "2026-01-02T00:00:00Z" },
    };
    render(
      <RemediationPanel
        remediation={approvedButAlreadyReported}
        findingId="f1"
        onMutated={() => {}}
      />,
    );
    expect(
      screen.queryByRole("button", { name: "Report Execution" }),
    ).not.toBeInTheDocument();
  });
});
