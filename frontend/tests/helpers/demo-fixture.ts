import type { DemoDataset } from "@/lib/demo/types";
import {
  resolveScenarioFacts,
  type ScenarioFacts,
} from "@/lib/demo/scenario-facts";
import { validateDataset } from "@/lib/demo/dataset-validation";

function ref(file: string, rowIndex: number) {
  return { file, rowIndex };
}

export function buildTestDemoDataset(
  overrides: Partial<{
    riskSeverity: string;
    sourcingPct: number;
    revenueUsd: number;
    candidateStatus: string;
    candidateCapacityPct: number;
    breakSupplierMaterialLink: boolean;
    duplicateSupplierId: boolean;
  }> = {},
): DemoDataset {
  const {
    riskSeverity = "Severe",
    sourcingPct = 100,
    revenueUsd = 48_000_000,
    candidateStatus = "Qualified",
    candidateCapacityPct = 60,
    breakSupplierMaterialLink = false,
    duplicateSupplierId = false,
  } = overrides;

  const parsed = {
    suppliers: {
      fileName: "suppliers.csv",
      columns: ["supplier_id", "supplier_name", "region_id"],
      sampleRows: [],
      records: [
        {
          supplierId: "SUP-001",
          supplierName: "Apex Components",
          regionId: "REG-EA",
          regionName: "East Asia Logistics Region",
          qualificationStatus: "Active",
          availableCapacityPct: 100,
          activationLeadTimeDays: 0,
          unitCostIndexPct: 100,
          sourceRef: ref("suppliers.csv", 0),
        },
        {
          supplierId: "SUP-002",
          supplierName: "Nova Energy Systems",
          regionId: "REG-NA",
          regionName: "North America Logistics Region",
          qualificationStatus: candidateStatus,
          availableCapacityPct: candidateCapacityPct,
          activationLeadTimeDays: 21,
          unitCostIndexPct: 107,
          sourceRef: ref("suppliers.csv", 1),
        },
        ...(duplicateSupplierId
          ? [
              {
                supplierId: "SUP-001",
                supplierName: "Apex Components (duplicate row)",
                regionId: "REG-EA",
                regionName: "East Asia Logistics Region",
                qualificationStatus: "Active",
                availableCapacityPct: 100,
                activationLeadTimeDays: 0,
                unitCostIndexPct: 100,
                sourceRef: ref("suppliers.csv", 2),
              },
            ]
          : []),
      ],
    },
    materials: {
      fileName: "materials.csv",
      columns: ["material_id", "material_name", "supplier_id"],
      sampleRows: [],
      records: [
        {
          materialId: "MAT-100",
          materialName: "Battery Cell BX-100",
          supplierId: breakSupplierMaterialLink ? "SUP-999" : "SUP-001",
          unitCostUsd: 42.5,
          sourceRef: ref("materials.csv", 0),
        },
      ],
    },
    products: {
      fileName: "products.csv",
      columns: ["product_id", "product_name", "material_id", "facility_id"],
      sampleRows: [],
      records: [
        {
          productId: "PROD-01",
          productName: "Atlas Pro Laptop",
          materialId: "MAT-100",
          facilityId: "FAC-01",
          sourceRef: ref("products.csv", 0),
        },
      ],
    },
    facilities: {
      fileName: "facilities.csv",
      columns: ["facility_id", "facility_name", "region_id"],
      sampleRows: [],
      records: [
        {
          facilityId: "FAC-01",
          facilityName: "Seattle Assembly Plant",
          regionId: "REG-NA",
          regionName: "North America Logistics Region",
          sourceRef: ref("facilities.csv", 0),
        },
      ],
    },
    supplyAgreements: {
      fileName: "supply_agreements.csv",
      columns: ["agreement_id", "material_id", "supplier_id", "sourcing_pct"],
      sampleRows: [],
      records: [
        {
          agreementId: "SA-100",
          materialId: "MAT-100",
          supplierId: "SUP-001",
          sourcingPct,
          terms: "Single-source; no alternate qualified at signing",
          sourceRef: ref("supply_agreements.csv", 0),
        },
      ],
    },
    riskEvents: {
      fileName: "risk_events.csv",
      columns: ["risk_event_id", "region_id", "severity"],
      sampleRows: [],
      records: [
        {
          riskEventId: "RE-001",
          regionId: "REG-EA",
          regionName: "East Asia Logistics Region",
          severity: riskSeverity,
          description:
            "Severe regional logistics disruption affecting East Asia Logistics Region",
          sourceRef: ref("risk_events.csv", 0),
        },
      ],
    },
    revenueExposure: {
      fileName: "revenue_exposure.csv",
      columns: ["product_id", "annual_revenue_usd"],
      sampleRows: [],
      records: [
        {
          productId: "PROD-01",
          annualRevenueUsd: revenueUsd,
          sourceRef: ref("revenue_exposure.csv", 0),
        },
      ],
    },
    relationshipKeys: [
      { fieldName: "supplier_id", files: ["suppliers.csv", "materials.csv"] },
      { fieldName: "material_id", files: ["materials.csv", "products.csv"] },
    ],
  };

  return {
    ...parsed,
    validationIssues: validateDataset({
      suppliers: parsed.suppliers.records,
      materials: parsed.materials.records,
      products: parsed.products.records,
      facilities: parsed.facilities.records,
      supplyAgreements: parsed.supplyAgreements.records,
      riskEvents: parsed.riskEvents.records,
      revenueExposure: parsed.revenueExposure.records,
    }),
  };
}

export function buildTestScenarioFacts(
  overrides: Parameters<typeof buildTestDemoDataset>[0] = {},
): ScenarioFacts {
  const resolution = resolveScenarioFacts(buildTestDemoDataset(overrides));
  if (!resolution.complete) {
    throw new Error(
      `Test fixture expected a complete scenario but got: ${resolution.reason}`,
    );
  }
  return resolution;
}
