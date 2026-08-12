import { expect, test } from "vitest";
import { validateDataset } from "@/lib/demo/dataset-validation";
import { buildTestDemoDataset } from "./helpers/demo-fixture";

function toValidatable(dataset: ReturnType<typeof buildTestDemoDataset>) {
  return {
    suppliers: dataset.suppliers.records,
    materials: dataset.materials.records,
    products: dataset.products.records,
    facilities: dataset.facilities.records,
    supplyAgreements: dataset.supplyAgreements.records,
    riskEvents: dataset.riskEvents.records,
    revenueExposure: dataset.revenueExposure.records,
  };
}

test("a well-formed dataset produces zero validation issues", () => {
  const issues = validateDataset(toValidatable(buildTestDemoDataset()));
  expect(issues).toHaveLength(0);
});

test("a duplicate primary key within a file is detected", () => {
  const dataset = buildTestDemoDataset({ duplicateSupplierId: true });
  expect(dataset.validationIssues.length).toBeGreaterThan(0);
  const duplicateIssue = dataset.validationIssues.find(
    (issue) => issue.file === "suppliers.csv" && issue.field === "supplier_id",
  );
  expect(duplicateIssue).toBeDefined();
  expect(duplicateIssue?.message).toContain("Duplicate supplier_id");
});

test("a broken foreign key is detected as a validation issue, not just an incomplete-evidence result downstream", () => {
  const dataset = buildTestDemoDataset({ breakSupplierMaterialLink: true });
  const brokenRefIssue = dataset.validationIssues.find(
    (issue) => issue.file === "materials.csv" && issue.field === "supplier_id",
  );
  expect(brokenRefIssue).toBeDefined();
  expect(brokenRefIssue?.message).toContain(
    "does not match any record in suppliers.csv",
  );
});
