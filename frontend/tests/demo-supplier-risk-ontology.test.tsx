import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { OntologyExplorerStage } from "@/app/demo/supplier-risk/_components/ontology-explorer-stage";
import { buildOntologyModel } from "@/lib/demo/ontology-model";
import { buildTestScenarioFacts } from "./helpers/demo-fixture";

class MockResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

beforeEach(() => {
  vi.stubGlobal("ResizeObserver", MockResizeObserver);
});

test("renders the scenario nodes and impact summary", () => {
  const model = buildOntologyModel(buildTestScenarioFacts());
  render(<OntologyExplorerStage model={model} onContinue={() => {}} />);

  expect(screen.getByText("Apex Components")).toBeInTheDocument();
  expect(screen.getByText("Nova Energy Systems")).toBeInTheDocument();
  expect(screen.getByText("Battery Cell BX-100")).toBeInTheDocument();
  expect(screen.getByText("$48M")).toBeInTheDocument();
});

test("selecting a node shows its source evidence", () => {
  const model = buildOntologyModel(buildTestScenarioFacts());
  render(<OntologyExplorerStage model={model} onContinue={() => {}} />);

  fireEvent.click(screen.getByText("Apex Components"));

  const inspector = screen.getByTestId("node-inspector");
  expect(inspector).toHaveTextContent("Apex Components");
  expect(inspector).toHaveTextContent("suppliers.csv (row 1)");
});

test("Continue to Decision Flow advances the demo", () => {
  const model = buildOntologyModel(buildTestScenarioFacts());
  const onContinue = vi.fn();
  render(<OntologyExplorerStage model={model} onContinue={onContinue} />);

  fireEvent.click(
    screen.getByRole("button", { name: "Continue to Decision Flow" }),
  );
  expect(onContinue).toHaveBeenCalledTimes(1);
});
