import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { SchemaMappingStage } from "@/app/demo/supplier-risk/_components/schema-mapping-stage";

test("shows proposed business concepts for detected fields", () => {
  render(<SchemaMappingStage onBuildOntology={() => {}} />);
  expect(screen.getByText("Supplied by Supplier")).toBeInTheDocument();
  expect(screen.getByText("Assembled at Facility")).toBeInTheDocument();
});

test("technical details are hidden until the reviewer opts in", () => {
  render(<SchemaMappingStage onBuildOntology={() => {}} />);
  expect(
    screen.queryByText(/Relationship: Supplier —SUPPLIES→ Material/),
  ).not.toBeInTheDocument();

  fireEvent.click(screen.getByLabelText("Show technical details"));

  expect(
    screen.getByText(/Relationship: Supplier —SUPPLIES→ Material/),
  ).toBeInTheDocument();
});

test("a mapping can be marked changed, and Build Ontology advances the demo", () => {
  const onBuildOntology = vi.fn();
  render(<SchemaMappingStage onBuildOntology={onBuildOntology} />);

  const checkboxes = screen.getAllByRole("checkbox");
  // checkboxes[0] is the "Show technical details" toggle; mapping rows start at 1.
  fireEvent.click(checkboxes[1]);
  expect(screen.getAllByText("Changed")[0]).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Build Ontology" }));
  expect(onBuildOntology).toHaveBeenCalledTimes(1);
});
