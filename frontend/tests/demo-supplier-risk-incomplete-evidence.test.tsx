import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { IncompleteEvidenceNotice } from "@/app/demo/supplier-risk/_components/incomplete-evidence-notice";
import { resolveScenarioFacts } from "@/lib/demo/scenario-facts";
import { buildTestDemoDataset } from "./helpers/demo-fixture";

test("shows the broken relationship and reason when evidence is incomplete", () => {
  const resolution = resolveScenarioFacts(
    buildTestDemoDataset({ breakSupplierMaterialLink: true }),
  );
  if (resolution.complete) throw new Error("expected an incomplete resolution");

  render(
    <IncompleteEvidenceNotice
      resolution={resolution}
      stageLabel="Explore Ontology"
    />,
  );

  const notice = screen.getByTestId("incomplete-evidence-notice");
  expect(notice).toHaveTextContent("Supplier → Material (SUPPLIES)");
  expect(notice).toHaveTextContent("SUP-999");
  expect(screen.getByRole("alert")).toBeInTheDocument();
});
