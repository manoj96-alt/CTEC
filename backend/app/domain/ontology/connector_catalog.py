"""Connector catalog for the Ontology Studio. Maturity labels are honest:

- "Demo Connected": demo data genuinely enters through this connector's
  boundary in this repository. Currently none qualify — the supplier-risk
  demo data enters through the seed/API boundary directly, not a named
  external system connector.
- "Skeleton Available": a common connector definition exists (this file)
  describing configuration shape, but no working adapter is implemented.
- "Roadmap": no connector definition exists yet.
"""

from dataclasses import dataclass
from typing import Literal

ConnectorMaturity = Literal["Demo Connected", "Skeleton Available", "Roadmap"]


@dataclass(frozen=True, slots=True)
class ConnectorDefinition:
    connector_id: str
    display_name: str
    source_system_type: str
    authentication_type: str
    supported_object_categories: tuple[str, ...]
    configuration_schema_reference: str
    mapping_template_reference: str
    health_status: str
    maturity: ConnectorMaturity


CONNECTOR_CATALOG: tuple[ConnectorDefinition, ...] = (
    ConnectorDefinition(
        connector_id="sap-s4hana",
        display_name="SAP S/4HANA",
        source_system_type="ERP",
        authentication_type="OAuth2 (client credentials)",
        supported_object_categories=("Supplier", "Material", "BOM", "Product"),
        configuration_schema_reference="connectors/sap_s4hana/config.schema.json",
        mapping_template_reference="connectors/sap_s4hana/mapping_template.json",
        health_status="Not configured",
        maturity="Skeleton Available",
    ),
    ConnectorDefinition(
        connector_id="sap-ariba",
        display_name="SAP Ariba",
        source_system_type="Procurement",
        authentication_type="OAuth2 (client credentials)",
        supported_object_categories=("Supplier", "Contract"),
        configuration_schema_reference="connectors/sap_ariba/config.schema.json",
        mapping_template_reference="connectors/sap_ariba/mapping_template.json",
        health_status="Not configured",
        maturity="Skeleton Available",
    ),
    ConnectorDefinition(
        connector_id="salesforce",
        display_name="Salesforce",
        source_system_type="CRM",
        authentication_type="OAuth2 (authorization code)",
        supported_object_categories=("Supplier",),
        configuration_schema_reference="connectors/salesforce/config.schema.json",
        mapping_template_reference="connectors/salesforce/mapping_template.json",
        health_status="Not configured",
        maturity="Roadmap",
    ),
    ConnectorDefinition(
        connector_id="snowflake",
        display_name="Snowflake",
        source_system_type="Data Warehouse",
        authentication_type="Key pair / OAuth2",
        supported_object_categories=("Material", "Product", "Revenue Exposure"),
        configuration_schema_reference="connectors/snowflake/config.schema.json",
        mapping_template_reference="connectors/snowflake/mapping_template.json",
        health_status="Not configured",
        maturity="Skeleton Available",
    ),
    ConnectorDefinition(
        connector_id="databricks",
        display_name="Databricks",
        source_system_type="Data Platform / Lakehouse",
        authentication_type="Personal access token / OAuth2",
        supported_object_categories=("Material", "Product", "Revenue Exposure"),
        configuration_schema_reference="connectors/databricks/config.schema.json",
        mapping_template_reference="connectors/databricks/mapping_template.json",
        health_status="Not configured",
        maturity="Skeleton Available",
    ),
    ConnectorDefinition(
        connector_id="microsoft-fabric",
        display_name="Microsoft Fabric",
        source_system_type="Data Platform / Lakehouse",
        authentication_type="Microsoft Entra ID (OAuth2)",
        supported_object_categories=("Material", "Product", "Revenue Exposure"),
        configuration_schema_reference="connectors/microsoft_fabric/config.schema.json",
        mapping_template_reference="connectors/microsoft_fabric/mapping_template.json",
        health_status="Not configured",
        maturity="Roadmap",
    ),
    ConnectorDefinition(
        connector_id="document-repository",
        display_name="Document Repository",
        source_system_type="Unstructured Document Store",
        authentication_type="API key / OAuth2 (varies by provider)",
        supported_object_categories=("Contract", "Risk Event"),
        configuration_schema_reference="connectors/document_repository/config.schema.json",
        mapping_template_reference="connectors/document_repository/mapping_template.json",
        health_status="Not configured",
        maturity="Roadmap",
    ),
    ConnectorDefinition(
        connector_id="rest-api",
        display_name="REST API",
        source_system_type="Generic HTTP",
        authentication_type="Bearer token (OIDC/JWT)",
        supported_object_categories=("Supplier", "Material", "BOM", "Product", "Facility", "Contract", "Risk Event"),
        configuration_schema_reference="connectors/rest_api/config.schema.json",
        mapping_template_reference="connectors/rest_api/mapping_template.json",
        health_status="Available",
        maturity="Skeleton Available",
    ),
    ConnectorDefinition(
        connector_id="mcp",
        display_name="MCP",
        source_system_type="Model Context Protocol",
        authentication_type="Provider-defined",
        supported_object_categories=("Supplier", "Material", "BOM", "Product", "Facility", "Contract", "Risk Event"),
        configuration_schema_reference="connectors/mcp/config.schema.json",
        mapping_template_reference="connectors/mcp/mapping_template.json",
        health_status="Not configured",
        maturity="Roadmap",
    ),
)
