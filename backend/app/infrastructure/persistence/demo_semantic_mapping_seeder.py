"""Explicit, idempotent, demo-only seeder for the Gate H H3 deterministic
Source-to-Blueprint semantic mapping demonstration (CDD-019 §15, §22; H3
Deterministic Mapping Demonstration Artifact Authorization).

Never invoked by normal production bootstrap: app.main.lifespan only ever
builds the dependency Container -- nothing there, or anywhere else on the
request path, calls this module. It has its own, separate, manually-run
CLI entrypoint (see __main__ below) and must be invoked deliberately --
following demo_gate_f_seeder.py's exact precedent.

Refuses to seed any tenant other than the labeled demo tenant
(BOOTSTRAP_DEMO_TENANT_ID). Deterministically (`uuid5` under
BOOTSTRAP_SEED_NAMESPACE) and idempotently creates exactly: one
SourceSystem ("H3 Demo ERP"), one SourceObject ("LFA1"), one SourceField
("LFA1-NAME1", via the real, unmodified SourceFieldRepositoryImpl.create()),
and one Approved SemanticMapping from that field to the existing, real
"Supplier Legal Name" InformationElementRequirement (resolved by name via
the real, unmodified BlueprintApplicationService.get_approved_by_name(),
never created), via the real, unmodified SemanticMappingRepositoryImpl.
create(). "Risk Event Severity" is deliberately left unmapped -- the
required missing-mapping proof.

Calls BlueprintSeeder(session).load() first (idempotent) to guarantee the
canonical Blueprint and its two InformationElementRequirements exist,
regardless of invocation order.

Idempotent: every id used is deterministic (uuid5, namespaced under the
existing BOOTSTRAP_SEED_NAMESPACE), and every write is preceded by an
existence check, so running seed() twice against the same database
creates nothing new the second time.
"""

from dataclasses import dataclass
from uuid import UUID, uuid5

from sqlalchemy.orm import Session

from app.application.blueprint_service import BlueprintApplicationService
from app.core.bootstrap import (
    BOOTSTRAP_DEMO_TENANT_ID,
    BOOTSTRAP_SEED_NAMESPACE,
    BOOTSTRAP_SYSTEM_ENTITY_ID,
    SEED_TIMESTAMP,
)
from app.domain.integration import SourceField
from app.domain.semantic_mapping import SemanticMapping
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import CanonicalName, Identifier
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.blueprint_seed import (
    CANONICAL_BLUEPRINT_NAME,
    BlueprintSeeder,
)
from app.infrastructure.persistence.models.source_object import SourceObject as SourceObjectORM
from app.infrastructure.persistence.models.source_system import SourceSystem as SourceSystemORM
from app.infrastructure.persistence.semantic_mapping_repository import (
    SemanticMappingRepositoryImpl,
)
from app.infrastructure.persistence.source_field_repository import SourceFieldRepositoryImpl

SEED_VERSION = "H3-DEMO-MAPPING-V1"

SOURCE_SYSTEM_NAME = "H3 Demo ERP"
SOURCE_OBJECT_NAME = "LFA1"
SOURCE_FIELD_LABEL = "LFA1-NAME1"
MAPPED_ELEMENT_NAME = "Supplier Legal Name"


class DemoTenantRequiredError(Exception):
    """Raised when the seeder is asked to seed any tenant other than the
    labeled demo tenant."""


@dataclass(frozen=True, slots=True)
class DemoSemanticMappingSeedSummary:
    tenant_id: str
    source_system_id: UUID
    source_object_id: UUID
    source_field_id: UUID
    semantic_mapping_id: UUID
    information_element_requirement_id: UUID


class DemoSemanticMappingSeeder:
    """Deterministically persists the H3 demonstration mapping. Idempotent:
    safe to call repeatedly."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def seed(self, tenant_id: str = BOOTSTRAP_DEMO_TENANT_ID) -> DemoSemanticMappingSeedSummary:
        if tenant_id != BOOTSTRAP_DEMO_TENANT_ID:
            raise DemoTenantRequiredError(
                f"The demo semantic mapping seeder refuses to seed tenant {tenant_id!r}; "
                f"it only ever seeds the labeled demo tenant {BOOTSTRAP_DEMO_TENANT_ID!r}."
            )

        BlueprintSeeder(self._session).load()
        self._session.flush()

        element_id = self._information_element_requirement_id(MAPPED_ELEMENT_NAME)
        source_system_id = self._seed_source_system(tenant_id)
        source_object_id = self._seed_source_object(tenant_id, source_system_id)
        source_field_id = self._seed_source_field(source_object_id)
        semantic_mapping_id = self._seed_semantic_mapping(source_field_id, element_id)

        return DemoSemanticMappingSeedSummary(
            tenant_id=tenant_id,
            source_system_id=source_system_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            semantic_mapping_id=semantic_mapping_id,
            information_element_requirement_id=element_id,
        )

    def _information_element_requirement_id(self, element_name: str) -> UUID:
        blueprint = BlueprintApplicationService(
            repository=BlueprintRepositoryImpl(self._session)
        ).get_approved_by_name(CANONICAL_BLUEPRINT_NAME)
        if blueprint is None:
            raise ValidationException(
                f"Required canonical Blueprint not found: {CANONICAL_BLUEPRINT_NAME}"
            )
        for concept_requirement in blueprint.concept_requirements:
            for element in concept_requirement.information_element_requirements:
                if element.element_name.value == element_name:
                    return element.information_element_requirement_id.value
        raise ValidationException(
            f"Required InformationElementRequirement not found: {element_name}"
        )

    def _seed_source_system(self, tenant_id: str) -> UUID:
        identifier = self._stable_id(f"source-system:{SOURCE_SYSTEM_NAME}")
        if self._session.get(SourceSystemORM, identifier) is None:
            self._session.add(
                SourceSystemORM(
                    source_system_id=identifier,
                    tenant_id=tenant_id,
                    source_system_name=SOURCE_SYSTEM_NAME,
                    lifecycle_state="Active",
                    effective_from=SEED_TIMESTAMP,
                    governance_status="Approved",
                    created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                    created_on=SEED_TIMESTAMP,
                )
            )
            self._session.flush()
        return identifier

    def _seed_source_object(self, tenant_id: str, source_system_id: UUID) -> UUID:
        identifier = self._stable_id(f"source-object:{SOURCE_OBJECT_NAME}")
        if self._session.get(SourceObjectORM, identifier) is None:
            self._session.add(
                SourceObjectORM(
                    source_object_id=identifier,
                    tenant_id=tenant_id,
                    source_object_name=SOURCE_OBJECT_NAME,
                    lifecycle_state="Active",
                    effective_from=SEED_TIMESTAMP,
                    governance_status="Approved",
                    created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                    created_on=SEED_TIMESTAMP,
                    source_system_id=source_system_id,
                )
            )
            self._session.flush()
        return identifier

    def _seed_source_field(self, source_object_id: UUID) -> UUID:
        identifier = self._stable_id(f"source-field:{SOURCE_FIELD_LABEL}")
        repository = SourceFieldRepositoryImpl(self._session)
        if repository.get_by_id(identifier) is None:
            repository.create(
                SourceField(
                    source_field_id=Identifier(identifier),
                    source_object_id=Identifier(source_object_id),
                    field_label=CanonicalName(SOURCE_FIELD_LABEL),
                    lifecycle_state=LifecycleState.ACTIVE,
                    governance_status=GovernanceStatus.APPROVED,
                    created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
                    created_on=SEED_TIMESTAMP,
                )
            )
            self._session.flush()
        return identifier

    def _seed_semantic_mapping(self, source_field_id: UUID, element_id: UUID) -> UUID:
        identifier = self._stable_id(f"semantic-mapping:{SOURCE_FIELD_LABEL}")
        repository = SemanticMappingRepositoryImpl(self._session)
        if repository.get_by_id(identifier) is None:
            repository.create(
                SemanticMapping(
                    semantic_mapping_id=Identifier(identifier),
                    source_field_id=Identifier(source_field_id),
                    information_element_requirement_id=Identifier(element_id),
                    lifecycle_state=LifecycleState.ACTIVE,
                    governance_status=GovernanceStatus.APPROVED,
                    created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
                    created_on=SEED_TIMESTAMP,
                )
            )
            self._session.flush()
        return identifier

    @staticmethod
    def _stable_id(value: str) -> UUID:
        return uuid5(BOOTSTRAP_SEED_NAMESPACE, f"{SEED_VERSION}:{value}")


if __name__ == "__main__":
    from app.core.config import get_settings
    from app.infrastructure.persistence.database import create_database_engine
    from app.infrastructure.persistence.session import create_session_factory

    settings = get_settings()
    engine = create_database_engine(settings)
    sessions = create_session_factory(engine)
    with sessions.begin() as cli_session:
        result = DemoSemanticMappingSeeder(cli_session).seed()
    print(result)
