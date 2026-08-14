from datetime import datetime
from uuid import UUID

BOOTSTRAP_SYSTEM_ENTITY_ID = UUID("00000000-0000-0000-0000-000000000001")
BOOTSTRAP_SYSTEM_NAME = "ECOM Bootstrap System"
BOOTSTRAP_SYSTEM_BUSINESS_NAME = "ECOM Bootstrap System"
BOOTSTRAP_ENTITY_TYPE = "System Actor"
BOOTSTRAP_STATUS = "Active"
SEED_TIMESTAMP = datetime.fromisoformat("2026-01-01T00:00:00+00:00")
SEED_VERSION = "EDT-001-V3"

# Implementation support constants. Not part of the Canonical Logical Model.
# Required solely to satisfy referential integrity during deterministic bootstrap;
# these identities do not introduce additional business entities or attributes.
BOOTSTRAP_ENTERPRISE_TYPE_ID = UUID("00000000-0000-0000-0000-000000000002")
BOOTSTRAP_COUNTRY_ID = UUID("00000000-0000-0000-0000-000000000003")
BOOTSTRAP_ENTERPRISE_ID = UUID("00000000-0000-0000-0000-000000000004")
BOOTSTRAP_BUSINESS_DOMAIN_ID = UUID("00000000-0000-0000-0000-000000000005")
BOOTSTRAP_INSTITUTIONAL_CONCEPT_ID = UUID("00000000-0000-0000-0000-000000000006")
BOOTSTRAP_ENTITY_TYPE_ID = UUID("00000000-0000-0000-0000-000000000007")

BOOTSTRAP_ENTERPRISE_TYPE_NAME = "System"
BOOTSTRAP_COUNTRY_NAME = "Unspecified"
BOOTSTRAP_COUNTRY_ISO2 = "ZZ"
BOOTSTRAP_COUNTRY_ISO3 = "ZZZ"
BOOTSTRAP_ENTERPRISE_NAME = "ECOM Platform"
BOOTSTRAP_BUSINESS_DOMAIN_NAME = "Platform Operations"
BOOTSTRAP_GOVERNANCE_STATUS = "Approved"
BOOTSTRAP_SEED_NAMESPACE = UUID("00000000-0000-0000-0000-000000000008")

# A demo/reference tenant label used only to stamp seeded and demo data
# (EDT-001 provenance, Entity Resolution demo cases). This is not a governed
# tenant identity issued by any identity provider; real tenant_id values are
# always sourced from the authenticated OIDC tenant claim at the trusted
# boundary (see app.api.supplier_risk.authentication.TrustedPrincipal).
BOOTSTRAP_DEMO_TENANT_ID = "ctec-demo-tenant"
