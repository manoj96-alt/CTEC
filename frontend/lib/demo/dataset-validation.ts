// Import-time dataset validation. Computed purely from already-parsed
// typed records — no fetching here, so this is testable in isolation.
// Explicit per-file checks rather than generic reflection: this demo has a
// fixed seven-file schema, so explicit checks stay clearer and easier to
// maintain than a generic rule engine would be for this scope.

import type {
  FacilityRecord,
  MaterialRecord,
  ProductRecord,
  RevenueExposureRecord,
  RiskEventRecord,
  SupplierRecord,
  SupplyAgreementRecord,
  ValidationIssue,
} from "./types";

export type { ValidationIssue };

export interface ValidatableDataset {
  suppliers: SupplierRecord[];
  materials: MaterialRecord[];
  products: ProductRecord[];
  facilities: FacilityRecord[];
  supplyAgreements: SupplyAgreementRecord[];
  riskEvents: RiskEventRecord[];
  revenueExposure: RevenueExposureRecord[];
}

function findDuplicates<T>(
  records: T[],
  fileName: string,
  fieldName: string,
  getId: (record: T) => string,
  getRowIndex: (record: T) => number,
): ValidationIssue[] {
  const seen = new Map<string, number>();
  const issues: ValidationIssue[] = [];
  for (const record of records) {
    const id = getId(record);
    const rowIndex = getRowIndex(record);
    if (seen.has(id)) {
      issues.push({
        severity: "error",
        file: fileName,
        rowIndex,
        field: fieldName,
        message: `Duplicate ${fieldName} "${id}" — first seen at row ${seen.get(id)! + 1}.`,
      });
    } else {
      seen.set(id, rowIndex);
    }
  }
  return issues;
}

function findBrokenReferences<T>(
  records: T[],
  fileName: string,
  fieldName: string,
  getForeignKey: (record: T) => string,
  getRowIndex: (record: T) => number,
  validIds: Set<string>,
  referencedFile: string,
): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  for (const record of records) {
    const foreignKey = getForeignKey(record);
    if (!validIds.has(foreignKey)) {
      issues.push({
        severity: "error",
        file: fileName,
        rowIndex: getRowIndex(record),
        field: fieldName,
        message: `${fieldName} "${foreignKey}" does not match any record in ${referencedFile}.`,
      });
    }
  }
  return issues;
}

export function validateDataset(
  dataset: ValidatableDataset,
): ValidationIssue[] {
  const issues: ValidationIssue[] = [];

  issues.push(
    ...findDuplicates(
      dataset.suppliers,
      "suppliers.csv",
      "supplier_id",
      (r) => r.supplierId,
      (r) => r.sourceRef.rowIndex,
    ),
    ...findDuplicates(
      dataset.materials,
      "materials.csv",
      "material_id",
      (r) => r.materialId,
      (r) => r.sourceRef.rowIndex,
    ),
    ...findDuplicates(
      dataset.products,
      "products.csv",
      "product_id",
      (r) => r.productId,
      (r) => r.sourceRef.rowIndex,
    ),
    ...findDuplicates(
      dataset.facilities,
      "facilities.csv",
      "facility_id",
      (r) => r.facilityId,
      (r) => r.sourceRef.rowIndex,
    ),
    ...findDuplicates(
      dataset.supplyAgreements,
      "supply_agreements.csv",
      "agreement_id",
      (r) => r.agreementId,
      (r) => r.sourceRef.rowIndex,
    ),
    ...findDuplicates(
      dataset.riskEvents,
      "risk_events.csv",
      "risk_event_id",
      (r) => r.riskEventId,
      (r) => r.sourceRef.rowIndex,
    ),
    ...findDuplicates(
      dataset.revenueExposure,
      "revenue_exposure.csv",
      "product_id",
      (r) => r.productId,
      (r) => r.sourceRef.rowIndex,
    ),
  );

  const supplierIds = new Set(dataset.suppliers.map((r) => r.supplierId));
  const materialIds = new Set(dataset.materials.map((r) => r.materialId));
  const facilityIds = new Set(dataset.facilities.map((r) => r.facilityId));
  const productIds = new Set(dataset.products.map((r) => r.productId));

  issues.push(
    ...findBrokenReferences(
      dataset.materials,
      "materials.csv",
      "supplier_id",
      (r) => r.supplierId,
      (r) => r.sourceRef.rowIndex,
      supplierIds,
      "suppliers.csv",
    ),
    ...findBrokenReferences(
      dataset.products,
      "products.csv",
      "material_id",
      (r) => r.materialId,
      (r) => r.sourceRef.rowIndex,
      materialIds,
      "materials.csv",
    ),
    ...findBrokenReferences(
      dataset.products,
      "products.csv",
      "facility_id",
      (r) => r.facilityId,
      (r) => r.sourceRef.rowIndex,
      facilityIds,
      "facilities.csv",
    ),
    ...findBrokenReferences(
      dataset.supplyAgreements,
      "supply_agreements.csv",
      "material_id",
      (r) => r.materialId,
      (r) => r.sourceRef.rowIndex,
      materialIds,
      "materials.csv",
    ),
    ...findBrokenReferences(
      dataset.supplyAgreements,
      "supply_agreements.csv",
      "supplier_id",
      (r) => r.supplierId,
      (r) => r.sourceRef.rowIndex,
      supplierIds,
      "suppliers.csv",
    ),
    ...findBrokenReferences(
      dataset.revenueExposure,
      "revenue_exposure.csv",
      "product_id",
      (r) => r.productId,
      (r) => r.sourceRef.rowIndex,
      productIds,
      "products.csv",
    ),
  );

  return issues;
}
