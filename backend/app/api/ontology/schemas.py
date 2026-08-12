from pydantic import BaseModel, ConfigDict


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConceptResponse(ClosedModel):
    entity_type_id: str
    name: str
    definition: str
    definition_source: str
    lifecycle_state: str
    governance_status: str
    version_number: int
    discovery_label: str


class RelationshipResponse(ClosedModel):
    relationship_type_id: str
    name: str
    source_concept: str
    target_concept: str
    lifecycle_state: str
    governance_status: str
    discovery_label: str


class QualityDimensionResponse(ClosedModel):
    dimension: str
    score: float
    passed: bool
    explanation: str


class QualityScoreResponse(ClosedModel):
    overall_score: float
    method: str
    dimensions: list[QualityDimensionResponse]
    passed_checks: list[str]
    failed_checks: list[str]


class ConnectorResponse(ClosedModel):
    connector_id: str
    display_name: str
    source_system_type: str
    authentication_type: str
    supported_object_categories: list[str]
    configuration_schema_reference: str
    mapping_template_reference: str
    health_status: str
    maturity: str


class OntologySummaryResponse(ClosedModel):
    ontology_id: str
    name: str
    description: str
    version: str
    status: str
    concept_count: int
    relationship_count: int
    quality: QualityScoreResponse
    activation_applications: list[str]


class OntologyDetailResponse(ClosedModel):
    ontology_id: str
    name: str
    description: str
    version: str
    status: str
    concepts: list[ConceptResponse]
    relationships: list[RelationshipResponse]
    source_mappings: list[str]
    provenance: str
    governance_metadata: str
    quality: QualityScoreResponse
    activation_applications: list[str]


class OntologyListResponse(ClosedModel):
    ontologies: list[OntologySummaryResponse]


class ConnectorListResponse(ClosedModel):
    connectors: list[ConnectorResponse]
