// Single centralized resolution step. Both the ontology model and the
// decision-rule engine consume THIS module's output rather than each
// independently re-querying the raw dataset — so there is exactly one place
// scenario facts get derived, and a broken relationship is reported once,
// consistently, instead of crashing wherever it happens to be looked up.

import type {
  DemoDataset,
  FacilityRecord,
  MaterialRecord,
  ProductRecord,
  RevenueExposureRecord,
  RiskEventRecord,
  SupplierRecord,
  SupplyAgreementRecord,
} from "./types";

export const PRIMARY_SUPPLIER_ID = "SUP-001";
export const PRIMARY_MATERIAL_ID = "MAT-100";
export const PRIMARY_PRODUCT_ID = "PROD-01";
export const CANDIDATE_SUPPLIER_ID = "SUP-002";

export interface ScenarioFacts {
  complete: true;
  supplier: SupplierRecord;
  candidate: SupplierRecord;
  material: MaterialRecord;
  product: ProductRecord;
  facility: FacilityRecord;
  agreement: SupplyAgreementRecord;
  riskEvent: RiskEventRecord;
  revenue: RevenueExposureRecord;
}

export interface IncompleteScenario {
  complete: false;
  brokenRelationship: string;
  reason: string;
}

export type ScenarioResolution = ScenarioFacts | IncompleteScenario;

function incomplete(
  brokenRelationship: string,
  reason: string,
): IncompleteScenario {
  return { complete: false, brokenRelationship, reason };
}

export function resolveScenarioFacts(dataset: DemoDataset): ScenarioResolution {
  const supplier = dataset.suppliers.records.find(
    (r) => r.supplierId === PRIMARY_SUPPLIER_ID,
  );
  if (!supplier) {
    return incomplete(
      "Supplier",
      `No supplier record found for ${PRIMARY_SUPPLIER_ID}.`,
    );
  }

  const candidate = dataset.suppliers.records.find(
    (r) => r.supplierId === CANDIDATE_SUPPLIER_ID,
  );
  if (!candidate) {
    return incomplete(
      "Candidate supplier",
      `No candidate supplier record found for ${CANDIDATE_SUPPLIER_ID}.`,
    );
  }

  const material = dataset.materials.records.find(
    (r) => r.materialId === PRIMARY_MATERIAL_ID,
  );
  if (!material) {
    return incomplete(
      "Material",
      `No material record found for ${PRIMARY_MATERIAL_ID}.`,
    );
  }

  // This is the relationship the "remove supplier-material link" scenario
  // test breaks: materials.csv's supplier_id no longer resolves to a real
  // supplier row.
  if (material.supplierId !== supplier.supplierId) {
    return incomplete(
      "Supplier → Material (SUPPLIES)",
      `${material.materialName} (${material.materialId}) references supplier ${material.supplierId}, ` +
        `which does not match the affected supplier ${supplier.supplierId}. The supply relationship ` +
        `could not be confirmed from imported data.`,
    );
  }

  const product = dataset.products.records.find(
    (r) => r.productId === PRIMARY_PRODUCT_ID,
  );
  if (!product) {
    return incomplete(
      "Product",
      `No product record found for ${PRIMARY_PRODUCT_ID}.`,
    );
  }
  if (product.materialId !== material.materialId) {
    return incomplete(
      "Material → Product (USED_IN)",
      `${product.productName} does not reference material ${material.materialId}. ` +
        `The affected-product path could not be confirmed from imported data.`,
    );
  }

  const facility = dataset.facilities.records.find(
    (r) => r.facilityId === product.facilityId,
  );
  if (!facility) {
    return incomplete(
      "Product → Facility (ASSEMBLED_AT)",
      `No facility record found for ${product.facilityId}.`,
    );
  }

  const agreement = dataset.supplyAgreements.records.find(
    (r) => r.materialId === material.materialId,
  );
  if (!agreement) {
    return incomplete(
      "Material → Supply Agreement (COVERED_BY)",
      `No supply agreement found covering ${material.materialId}.`,
    );
  }

  const riskEvent = dataset.riskEvents.records.find(
    (r) => r.regionId === supplier.regionId,
  );
  if (!riskEvent) {
    return incomplete(
      "Supplier → Region → Risk Event (AFFECTED_BY)",
      `No risk event found affecting region ${supplier.regionId}.`,
    );
  }

  const revenue = dataset.revenueExposure.records.find(
    (r) => r.productId === product.productId,
  );
  if (!revenue) {
    return incomplete(
      "Product → Revenue Exposure (GENERATES_REVENUE)",
      `No revenue exposure record found for ${product.productId}.`,
    );
  }

  return {
    complete: true,
    supplier,
    candidate,
    material,
    product,
    facility,
    agreement,
    riskEvent,
    revenue,
  };
}
