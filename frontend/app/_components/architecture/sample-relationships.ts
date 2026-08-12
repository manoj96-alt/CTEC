// SAMPLE SUPPLIER RISK RELATIONSHIPS — descriptive labels for the
// customer-facing Architecture page. These describe the entity TYPES
// (Supplier, Material, ...), not the specific sample company names shown
// in the working demo. Every edge label here is checked in
// tests/architecture-page.test.tsx against the real edges produced by
// lib/demo/ontology-model.ts, so this list cannot silently drift from the
// implemented ontology.

export interface SampleRelationship {
  source: string;
  label: string;
  target: string;
}

export const sampleRelationships: SampleRelationship[] = [
  { source: "Supplier", label: "supplies", target: "Material" },
  { source: "Material", label: "used in", target: "Product" },
  { source: "Product", label: "assembled at", target: "Facility" },
  {
    source: "Facility",
    label: "generates revenue",
    target: "Revenue Exposure",
  },
  { source: "Supplier", label: "located in", target: "Region" },
  { source: "Region", label: "affected by", target: "Risk Event" },
  { source: "Material", label: "covered by", target: "Supply Agreement" },
  {
    source: "Candidate Supplier",
    label: "candidate alternate for",
    target: "Material",
  },
];
