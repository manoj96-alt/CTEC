// CURATED SAMPLE DATASET METADATA.
//
// This file is descriptive only: business-friendly names, purposes, primary
// and foreign key designations, and reliably known display types /
// required-optional status. It does NOT duplicate records, record counts,
// column counts, validation outcomes, or scenario facts — those are always
// derived live from the loaded DemoDataset (lib/demo/fixture-loader.ts,
// lib/demo/dataset-validation.ts). If this file's field names ever drift
// from the real CSVs, tests/dataset-catalog.test.tsx catches it.

export type DisplayType =
  "Text" | "Identifier" | "Number" | "Percentage" | "Currency (USD)";

export type ColumnRole = "primary_key" | "foreign_key" | "attribute";

export interface CatalogColumn {
  field: string;
  displayType: DisplayType;
  required: boolean;
  role: ColumnRole;
  relationshipTarget?: string;
  // Set only when a field is simultaneously the file's primary key AND a
  // foreign key into another file — currently just revenue_exposure.csv's
  // product_id. `role` stays "foreign_key" for relationship-summary logic;
  // this flag is purely for accurate display of the combined designation.
  isPrimaryKey?: boolean;
}

export interface CatalogEntry {
  fileName: string;
  businessName: string;
  purpose: string;
  primaryKey: string;
  columns: CatalogColumn[];
}

export const datasetCatalog: CatalogEntry[] = [
  {
    fileName: "suppliers.csv",
    businessName: "Suppliers",
    purpose:
      "Suppliers who provide materials, with qualification and capacity attributes used to evaluate alternates.",
    primaryKey: "supplier_id",
    columns: [
      {
        field: "supplier_id",
        displayType: "Identifier",
        required: true,
        role: "primary_key",
      },
      {
        field: "supplier_name",
        displayType: "Text",
        required: true,
        role: "attribute",
      },
      {
        field: "region_id",
        displayType: "Identifier",
        required: true,
        role: "attribute",
      },
      {
        field: "region_name",
        displayType: "Text",
        required: true,
        role: "attribute",
      },
      {
        field: "qualification_status",
        displayType: "Text",
        required: true,
        role: "attribute",
      },
      {
        field: "available_capacity_pct",
        displayType: "Percentage",
        required: true,
        role: "attribute",
      },
      {
        field: "activation_lead_time_days",
        displayType: "Number",
        required: true,
        role: "attribute",
      },
      {
        field: "unit_cost_index_pct",
        displayType: "Percentage",
        required: true,
        role: "attribute",
      },
    ],
  },
  {
    fileName: "materials.csv",
    businessName: "Materials",
    purpose: "Materials sourced from suppliers and consumed by products.",
    primaryKey: "material_id",
    columns: [
      {
        field: "material_id",
        displayType: "Identifier",
        required: true,
        role: "primary_key",
      },
      {
        field: "material_name",
        displayType: "Text",
        required: true,
        role: "attribute",
      },
      {
        field: "supplier_id",
        displayType: "Identifier",
        required: true,
        role: "foreign_key",
        relationshipTarget: "suppliers.csv",
      },
      {
        field: "unit_cost_usd",
        displayType: "Currency (USD)",
        required: true,
        role: "attribute",
      },
    ],
  },
  {
    fileName: "products.csv",
    businessName: "Products",
    purpose:
      "Products that consume a material and are assembled at a facility.",
    primaryKey: "product_id",
    columns: [
      {
        field: "product_id",
        displayType: "Identifier",
        required: true,
        role: "primary_key",
      },
      {
        field: "product_name",
        displayType: "Text",
        required: true,
        role: "attribute",
      },
      {
        field: "material_id",
        displayType: "Identifier",
        required: true,
        role: "foreign_key",
        relationshipTarget: "materials.csv",
      },
      {
        field: "facility_id",
        displayType: "Identifier",
        required: true,
        role: "foreign_key",
        relationshipTarget: "facilities.csv",
      },
    ],
  },
  {
    fileName: "facilities.csv",
    businessName: "Facilities",
    purpose: "Assembly facilities where products are built.",
    primaryKey: "facility_id",
    columns: [
      {
        field: "facility_id",
        displayType: "Identifier",
        required: true,
        role: "primary_key",
      },
      {
        field: "facility_name",
        displayType: "Text",
        required: true,
        role: "attribute",
      },
      {
        field: "region_id",
        displayType: "Identifier",
        required: true,
        role: "attribute",
      },
      {
        field: "region_name",
        displayType: "Text",
        required: true,
        role: "attribute",
      },
    ],
  },
  {
    fileName: "supply_agreements.csv",
    businessName: "Supply Agreements",
    purpose:
      "Sourcing terms covering a material, including sourcing concentration used to assess single-source risk.",
    primaryKey: "agreement_id",
    columns: [
      {
        field: "agreement_id",
        displayType: "Identifier",
        required: true,
        role: "primary_key",
      },
      {
        field: "material_id",
        displayType: "Identifier",
        required: true,
        role: "foreign_key",
        relationshipTarget: "materials.csv",
      },
      {
        field: "supplier_id",
        displayType: "Identifier",
        required: true,
        role: "foreign_key",
        relationshipTarget: "suppliers.csv",
      },
      {
        field: "sourcing_pct",
        displayType: "Percentage",
        required: true,
        role: "attribute",
      },
      {
        field: "terms",
        displayType: "Text",
        required: false,
        role: "attribute",
      },
    ],
  },
  {
    fileName: "risk_events.csv",
    businessName: "Risk Events",
    purpose: "Disruption events affecting a region.",
    primaryKey: "risk_event_id",
    columns: [
      {
        field: "risk_event_id",
        displayType: "Identifier",
        required: true,
        role: "primary_key",
      },
      {
        field: "region_id",
        displayType: "Identifier",
        required: true,
        role: "attribute",
      },
      {
        field: "region_name",
        displayType: "Text",
        required: true,
        role: "attribute",
      },
      {
        field: "severity",
        displayType: "Text",
        required: true,
        role: "attribute",
      },
      {
        field: "description",
        displayType: "Text",
        required: true,
        role: "attribute",
      },
    ],
  },
  {
    fileName: "revenue_exposure.csv",
    businessName: "Revenue Exposure",
    purpose:
      "Annual revenue attributed to each product, used to calculate business impact.",
    primaryKey: "product_id",
    columns: [
      {
        field: "product_id",
        displayType: "Identifier",
        required: true,
        role: "foreign_key",
        relationshipTarget: "products.csv",
        isPrimaryKey: true,
      },
      {
        field: "annual_revenue_usd",
        displayType: "Currency (USD)",
        required: true,
        role: "attribute",
      },
    ],
  },
];
