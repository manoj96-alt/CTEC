// DEMO DATA MODEL — supports the guided supplier-risk demo only.
// Not connected to the production ontology, runtime, or persistence layer.

export interface SourceRef {
  file: string;
  rowIndex: number;
}

export interface ParsedFile<T> {
  fileName: string;
  columns: string[];
  sampleRows: Record<string, string>[];
  records: T[];
}

export interface SupplierRecord {
  supplierId: string;
  supplierName: string;
  regionId: string;
  regionName: string;
  qualificationStatus: string;
  availableCapacityPct: number;
  activationLeadTimeDays: number;
  unitCostIndexPct: number;
  sourceRef: SourceRef;
}

export interface MaterialRecord {
  materialId: string;
  materialName: string;
  supplierId: string;
  unitCostUsd: number;
  sourceRef: SourceRef;
}

export interface ProductRecord {
  productId: string;
  productName: string;
  materialId: string;
  facilityId: string;
  sourceRef: SourceRef;
}

export interface FacilityRecord {
  facilityId: string;
  facilityName: string;
  regionId: string;
  regionName: string;
  sourceRef: SourceRef;
}

export interface SupplyAgreementRecord {
  agreementId: string;
  materialId: string;
  supplierId: string;
  sourcingPct: number;
  terms: string;
  sourceRef: SourceRef;
}

export interface RiskEventRecord {
  riskEventId: string;
  regionId: string;
  regionName: string;
  severity: string;
  description: string;
  sourceRef: SourceRef;
}

export interface RevenueExposureRecord {
  productId: string;
  annualRevenueUsd: number;
  sourceRef: SourceRef;
}

export interface DemoDataset {
  suppliers: ParsedFile<SupplierRecord>;
  materials: ParsedFile<MaterialRecord>;
  products: ParsedFile<ProductRecord>;
  facilities: ParsedFile<FacilityRecord>;
  supplyAgreements: ParsedFile<SupplyAgreementRecord>;
  riskEvents: ParsedFile<RiskEventRecord>;
  revenueExposure: ParsedFile<RevenueExposureRecord>;
  relationshipKeys: DiscoveredRelationshipKey[];
  validationIssues: ValidationIssue[];
}

export interface ValidationIssue {
  severity: "error";
  file: string;
  rowIndex: number;
  field: string;
  message: string;
}

export interface DiscoveredRelationshipKey {
  fieldName: string;
  files: string[];
}
