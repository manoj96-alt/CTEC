export interface QualityDimension {
  dimension: string;
  score: number;
  passed: boolean;
  explanation: string;
}

export interface QualityScore {
  overall_score: number;
  method: string;
  dimensions: QualityDimension[];
  passed_checks: string[];
  failed_checks: string[];
}

export interface Concept {
  entity_type_id: string;
  name: string;
  definition: string;
  definition_source: string;
  lifecycle_state: string;
  governance_status: string;
  version_number: number;
  discovery_label: string;
}

export interface Relationship {
  relationship_type_id: string;
  name: string;
  source_concept: string;
  target_concept: string;
  lifecycle_state: string;
  governance_status: string;
  discovery_label: string;
}

export interface OntologySummary {
  ontology_id: string;
  name: string;
  description: string;
  version: string;
  status: string;
  concept_count: number;
  relationship_count: number;
  quality: QualityScore;
  activation_applications: string[];
}

export interface OntologyDetail {
  ontology_id: string;
  name: string;
  description: string;
  version: string;
  status: string;
  concepts: Concept[];
  relationships: Relationship[];
  source_mappings: string[];
  provenance: string;
  governance_metadata: string;
  quality: QualityScore;
  activation_applications: string[];
}

export interface Connector {
  connector_id: string;
  display_name: string;
  source_system_type: string;
  authentication_type: string;
  supported_object_categories: string[];
  configuration_schema_reference: string;
  mapping_template_reference: string;
  health_status: string;
  maturity: "Demo Connected" | "Skeleton Available" | "Roadmap";
}
