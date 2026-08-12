import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { loadDemoDataset } from "@/lib/demo/fixture-loader";
import { ImportDataStage } from "@/app/demo/supplier-risk/_components/import-data-stage";
import { buildTestDemoDataset } from "./helpers/demo-fixture";

const CSV_FIXTURES: Record<string, string> = {
  "suppliers.csv":
    "supplier_id,supplier_name,region_id,region_name,qualification_status,available_capacity_pct,activation_lead_time_days,unit_cost_index_pct\n" +
    "SUP-001,Apex Components,REG-EA,East Asia Logistics Region,Active,100,0,100\n" +
    "SUP-002,Nova Energy Systems,REG-NA,North America Logistics Region,Qualified,60,21,107\n",
  "materials.csv":
    "material_id,material_name,supplier_id,unit_cost_usd\nMAT-100,Battery Cell BX-100,SUP-001,42.50\n",
  "products.csv":
    "product_id,product_name,material_id,facility_id\nPROD-01,Atlas Pro Laptop,MAT-100,FAC-01\n",
  "facilities.csv":
    "facility_id,facility_name,region_id,region_name\nFAC-01,Seattle Assembly Plant,REG-NA,North America Logistics Region\n",
  "supply_agreements.csv":
    "agreement_id,material_id,supplier_id,sourcing_pct,terms\nSA-100,MAT-100,SUP-001,100,Single-source\n",
  "risk_events.csv":
    "risk_event_id,region_id,region_name,severity,description\nRE-001,REG-EA,East Asia Logistics Region,Severe,Severe regional logistics disruption\n",
  "revenue_exposure.csv": "product_id,annual_revenue_usd\nPROD-01,48000000\n",
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string) => {
      const fileName = String(input).split("/").pop() as string;
      const text = CSV_FIXTURES[fileName];
      return Promise.resolve({
        ok: true,
        text: () => Promise.resolve(text),
      } as Response);
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

test("loadDemoDataset parses all seven files and discovers relationship keys", async () => {
  const dataset = await loadDemoDataset();

  expect(dataset.suppliers.records).toHaveLength(2);
  expect(dataset.suppliers.records[0].supplierName).toBe("Apex Components");
  expect(dataset.materials.records[0].materialName).toBe("Battery Cell BX-100");
  expect(dataset.revenueExposure.records[0].annualRevenueUsd).toBe(48_000_000);

  const supplierIdKey = dataset.relationshipKeys.find(
    (key) => key.fieldName === "supplier_id",
  );
  expect(supplierIdKey?.files).toEqual(
    expect.arrayContaining([
      "suppliers.csv",
      "materials.csv",
      "supply_agreements.csv",
    ]),
  );
});

test("ImportDataStage renders the alert to load data before a dataset exists", () => {
  render(
    <ImportDataStage
      dataset={null}
      loading={false}
      error={null}
      onLoadSampleDataset={() => {}}
      onContinue={() => {}}
    />,
  );
  expect(
    screen.getByRole("button", { name: "Load Sample Dataset" }),
  ).toBeInTheDocument();
});

test("ImportDataStage shows file cards, row counts, and discovered keys once loaded", () => {
  const dataset = buildTestDemoDataset();
  render(
    <ImportDataStage
      dataset={dataset}
      loading={false}
      error={null}
      onLoadSampleDataset={() => {}}
      onContinue={() => {}}
    />,
  );
  expect(screen.getByText("suppliers.csv")).toBeInTheDocument();
  expect(screen.getByText(/2 rows detected/)).toBeInTheDocument();
  expect(screen.getByText(/supplier_id — links/)).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Continue to Schema Mapping" }),
  ).toBeInTheDocument();
});
