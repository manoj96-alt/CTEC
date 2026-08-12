import { parseCsv } from "./csv-parser";
import { validateDataset } from "./dataset-validation";
import type {
  DemoDataset,
  DiscoveredRelationshipKey,
  FacilityRecord,
  MaterialRecord,
  ParsedFile,
  ProductRecord,
  RevenueExposureRecord,
  RiskEventRecord,
  SourceRef,
  SupplierRecord,
  SupplyAgreementRecord,
} from "./types";

const DEMO_DATA_BASE_PATH = "/demo-data";

async function fetchCsv(
  fileName: string,
): Promise<{ text: string; raw: ReturnType<typeof parseCsv> }> {
  const response = await fetch(`${DEMO_DATA_BASE_PATH}/${fileName}`);
  if (!response.ok) {
    throw new Error(`Failed to load demo dataset file: ${fileName}`);
  }
  const text = await response.text();
  return { text, raw: parseCsv(text) };
}

function ref(fileName: string, rowIndex: number): SourceRef {
  return { file: fileName, rowIndex };
}

function toParsedFile<T>(
  fileName: string,
  raw: ReturnType<typeof parseCsv>,
  records: T[],
): ParsedFile<T> {
  return {
    fileName,
    columns: raw.columns,
    sampleRows: raw.rows.slice(0, 3),
    records,
  };
}

function discoverRelationshipKeys(
  filesToColumns: Record<string, string[]>,
): DiscoveredRelationshipKey[] {
  const fieldToFiles = new Map<string, string[]>();
  for (const [file, columns] of Object.entries(filesToColumns)) {
    for (const column of columns) {
      if (!column.endsWith("_id")) continue;
      const existing = fieldToFiles.get(column) ?? [];
      existing.push(file);
      fieldToFiles.set(column, existing);
    }
  }
  return Array.from(fieldToFiles.entries())
    .filter(([, files]) => files.length > 1)
    .map(([fieldName, files]) => ({ fieldName, files }));
}

export async function loadDemoDataset(): Promise<DemoDataset> {
  const [
    suppliersCsv,
    materialsCsv,
    productsCsv,
    facilitiesCsv,
    agreementsCsv,
    riskEventsCsv,
    revenueCsv,
  ] = await Promise.all([
    fetchCsv("suppliers.csv"),
    fetchCsv("materials.csv"),
    fetchCsv("products.csv"),
    fetchCsv("facilities.csv"),
    fetchCsv("supply_agreements.csv"),
    fetchCsv("risk_events.csv"),
    fetchCsv("revenue_exposure.csv"),
  ]);

  const suppliers: SupplierRecord[] = suppliersCsv.raw.rows.map(
    (row, index) => ({
      supplierId: row.supplier_id,
      supplierName: row.supplier_name,
      regionId: row.region_id,
      regionName: row.region_name,
      qualificationStatus: row.qualification_status,
      availableCapacityPct: Number(row.available_capacity_pct),
      activationLeadTimeDays: Number(row.activation_lead_time_days),
      unitCostIndexPct: Number(row.unit_cost_index_pct),
      sourceRef: ref("suppliers.csv", index),
    }),
  );

  const materials: MaterialRecord[] = materialsCsv.raw.rows.map(
    (row, index) => ({
      materialId: row.material_id,
      materialName: row.material_name,
      supplierId: row.supplier_id,
      unitCostUsd: Number(row.unit_cost_usd),
      sourceRef: ref("materials.csv", index),
    }),
  );

  const products: ProductRecord[] = productsCsv.raw.rows.map((row, index) => ({
    productId: row.product_id,
    productName: row.product_name,
    materialId: row.material_id,
    facilityId: row.facility_id,
    sourceRef: ref("products.csv", index),
  }));

  const facilities: FacilityRecord[] = facilitiesCsv.raw.rows.map(
    (row, index) => ({
      facilityId: row.facility_id,
      facilityName: row.facility_name,
      regionId: row.region_id,
      regionName: row.region_name,
      sourceRef: ref("facilities.csv", index),
    }),
  );

  const supplyAgreements: SupplyAgreementRecord[] = agreementsCsv.raw.rows.map(
    (row, index) => ({
      agreementId: row.agreement_id,
      materialId: row.material_id,
      supplierId: row.supplier_id,
      sourcingPct: Number(row.sourcing_pct),
      terms: row.terms,
      sourceRef: ref("supply_agreements.csv", index),
    }),
  );

  const riskEvents: RiskEventRecord[] = riskEventsCsv.raw.rows.map(
    (row, index) => ({
      riskEventId: row.risk_event_id,
      regionId: row.region_id,
      regionName: row.region_name,
      severity: row.severity,
      description: row.description,
      sourceRef: ref("risk_events.csv", index),
    }),
  );

  const revenueExposure: RevenueExposureRecord[] = revenueCsv.raw.rows.map(
    (row, index) => ({
      productId: row.product_id,
      annualRevenueUsd: Number(row.annual_revenue_usd),
      sourceRef: ref("revenue_exposure.csv", index),
    }),
  );

  const relationshipKeys = discoverRelationshipKeys({
    "suppliers.csv": suppliersCsv.raw.columns,
    "materials.csv": materialsCsv.raw.columns,
    "products.csv": productsCsv.raw.columns,
    "facilities.csv": facilitiesCsv.raw.columns,
    "supply_agreements.csv": agreementsCsv.raw.columns,
    "risk_events.csv": riskEventsCsv.raw.columns,
    "revenue_exposure.csv": revenueCsv.raw.columns,
  });

  const validationIssues = validateDataset({
    suppliers,
    materials,
    products,
    facilities,
    supplyAgreements,
    riskEvents,
    revenueExposure,
  });

  return {
    suppliers: toParsedFile("suppliers.csv", suppliersCsv.raw, suppliers),
    materials: toParsedFile("materials.csv", materialsCsv.raw, materials),
    products: toParsedFile("products.csv", productsCsv.raw, products),
    facilities: toParsedFile("facilities.csv", facilitiesCsv.raw, facilities),
    supplyAgreements: toParsedFile(
      "supply_agreements.csv",
      agreementsCsv.raw,
      supplyAgreements,
    ),
    riskEvents: toParsedFile("risk_events.csv", riskEventsCsv.raw, riskEvents),
    revenueExposure: toParsedFile(
      "revenue_exposure.csv",
      revenueCsv.raw,
      revenueExposure,
    ),
    relationshipKeys,
    validationIssues,
  };
}
