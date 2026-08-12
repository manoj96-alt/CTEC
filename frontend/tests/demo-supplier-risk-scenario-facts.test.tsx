import { expect, test } from "vitest";
import { resolveScenarioFacts } from "@/lib/demo/scenario-facts";
import { buildTestDemoDataset } from "./helpers/demo-fixture";

test("resolves a complete scenario from a well-formed dataset", () => {
  const resolution = resolveScenarioFacts(buildTestDemoDataset());
  expect(resolution.complete).toBe(true);
  if (resolution.complete) {
    expect(resolution.supplier.supplierName).toBe("Apex Components");
    expect(resolution.candidate.supplierName).toBe("Nova Energy Systems");
  }
});

test("removing the supplier-material relationship produces a clear incomplete-evidence result instead of throwing", () => {
  const dataset = buildTestDemoDataset({ breakSupplierMaterialLink: true });

  expect(() => resolveScenarioFacts(dataset)).not.toThrow();

  const resolution = resolveScenarioFacts(dataset);
  expect(resolution.complete).toBe(false);
  if (!resolution.complete) {
    expect(resolution.brokenRelationship).toBe(
      "Supplier → Material (SUPPLIES)",
    );
    expect(resolution.reason).toContain("SUP-999");
  }
});
