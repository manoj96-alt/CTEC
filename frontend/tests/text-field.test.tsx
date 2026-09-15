import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TextField } from "../components/design-system/text-field";

describe("TextField", () => {
  it("renders a visible, labeled input associated by htmlFor/id", () => {
    render(<TextField label="Blueprint name" value="" onChange={() => {}} />);
    const input = screen.getByLabelText("Blueprint name");
    expect(input).toBeInTheDocument();
    expect(input).toHaveClass("obs-text-field-input");
  });

  it("accepts input and calls onChange", () => {
    const onChange = vi.fn();
    render(<TextField label="Blueprint name" value="" onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Blueprint name"), {
      target: { value: "a" },
    });
    expect(onChange).toHaveBeenCalled();
  });

  it("is reachable via keyboard focus", () => {
    render(<TextField label="Blueprint name" value="" onChange={() => {}} />);
    const input = screen.getByLabelText("Blueprint name");
    input.focus();
    expect(input).toHaveFocus();
  });

  it("renders the disabled state", () => {
    render(
      <TextField
        label="Blueprint name"
        value=""
        onChange={() => {}}
        disabled
      />,
    );
    expect(screen.getByLabelText("Blueprint name")).toBeDisabled();
  });

  it("renders an error message, associated via aria-describedby, and marks the field invalid", () => {
    render(
      <TextField
        label="Blueprint name"
        value=""
        onChange={() => {}}
        error="This field is required."
      />,
    );
    const input = screen.getByLabelText("Blueprint name");
    expect(input).toHaveAttribute("aria-invalid", "true");
    const describedBy = input.getAttribute("aria-describedby");
    expect(describedBy).toBeTruthy();
    const errorEl = screen.getByRole("alert");
    expect(errorEl).toHaveTextContent("This field is required.");
    expect(errorEl.id).toBe(describedBy);
  });

  it("does not render an error state when no error is passed", () => {
    render(<TextField label="Blueprint name" value="" onChange={() => {}} />);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Blueprint name")).not.toHaveAttribute(
      "aria-invalid",
    );
  });
});
