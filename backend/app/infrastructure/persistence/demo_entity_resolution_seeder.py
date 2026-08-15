"""Explicit, idempotent, demo-only seeder for the TSMC Entity Resolution
Steward demonstration cases (Increment 3A Gate C).

Never invoked by normal production bootstrap: app.main.lifespan only ever
builds the dependency Container (see app/main.py) -- nothing there, or
anywhere else on the request path, calls this module. It has its own,
separate, manually-run CLI entrypoint (see __main__ below) and must be
invoked deliberately.

Refuses to seed any tenant other than the labeled demo tenant
(BOOTSTRAP_DEMO_TENANT_ID). Persists three honest evidence cases against
three distinct pairs of TSMC / TSMC Inc. / Taiwan Semiconductor
Manufacturing Company Limited source representations (each pair maps to
its own understanding_key, so the three cases are genuinely independent
rows, not one case re-appended three times), differing only in the
presence/agreement of a strong identifier (a clearly-labeled fictional
demo tax-registration value -- never a real supplier registration number):

  - no strong identifier               -> Possible Resolution / Medium
  - matching strong identifier         -> Resolved / High
  - conflicting strong identifiers     -> Blocked Conflict

Idempotent: every id used is deterministic (uuid5, namespaced under the
existing BOOTSTRAP_SEED_NAMESPACE), and every write is preceded by an
existence check, so running seed() twice against the same database creates
nothing new the second time.
"""

from dataclasses import dataclass
from uuid import UUID, uuid5

from sqlalchemy.orm import Session

from app.core.bootstrap import (
    BOOTSTRAP_BUSINESS_DOMAIN_ID,
    BOOTSTRAP_DEMO_TENANT_ID,
    BOOTSTRAP_ENTITY_TYPE_ID,
    BOOTSTRAP_SEED_NAMESPACE,
    BOOTSTRAP_SYSTEM_ENTITY_ID,
    SEED_TIMESTAMP,
)
from app.domain.identity_resolution.evidence import SourceRepresentation
from app.domain.identity_resolution.model import EvidenceType
from app.domain.identity_resolution.policy import conservative_preset
from app.domain.identity_resolution.service import EvidenceResolutionEngine
from app.infrastructure.persistence.entity_resolution_store import EntityResolutionStore
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.source_object import SourceObject
from app.infrastructure.persistence.models.source_system import SourceSystem
from app.infrastructure.persistence.resolution_policy_store import ResolutionPolicyStore

CANDIDATE_NAME = "Taiwan Semiconductor Manufacturing Company Limited"

# Clearly-labeled fictional demonstration values -- never real supplier
# registration numbers.
_MATCHING_TAX_ID = "DEMO-TAX-REG-000TSMC01"
_CONFLICTING_TAX_ID_CRM = "DEMO-TAX-REG-CRM-CONFLICT-A"
_CONFLICTING_TAX_ID_REGISTRY = "DEMO-TAX-REG-REGISTRY-CONFLICT-B"


def _demo_id(label: str) -> UUID:
    """Deterministic id for a fixed demo label: re-running the seeder
    against the same database always derives the same ids, making the
    existence checks below meaningful (idempotency)."""
    return uuid5(BOOTSTRAP_SEED_NAMESPACE, f"erm-demo:{label}")


_CRM_SYSTEM_ID = _demo_id("source-system:crm")
_REGISTRY_SYSTEM_ID = _demo_id("source-system:registry")

_CASE_A_CRM_OBJECT_ID = _demo_id("source-object:crm:case-a-no-strong-id")
_CASE_A_REGISTRY_OBJECT_ID = _demo_id("source-object:registry:case-a-no-strong-id")
_CASE_A_ENTITY_ID = _demo_id("enterprise-entity:case-a-no-strong-id")

_CASE_B_CRM_OBJECT_ID = _demo_id("source-object:crm:case-b-matching-strong-id")
_CASE_B_REGISTRY_OBJECT_ID = _demo_id("source-object:registry:case-b-matching-strong-id")
_CASE_B_ENTITY_ID = _demo_id("enterprise-entity:case-b-matching-strong-id")

_CASE_C_CRM_OBJECT_ID = _demo_id("source-object:crm:case-c-conflicting-strong-id")
_CASE_C_REGISTRY_OBJECT_ID = _demo_id("source-object:registry:case-c-conflicting-strong-id")
# Case C resolves to BLOCKED_CONFLICT, an entity-free outcome (see
# EnterpriseEntityResolutionRecord.__post_init__) -- no candidate entity id.


class DemoTenantRequiredError(Exception):
    """Raised when the seeder is asked to seed any tenant other than the
    labeled demo tenant."""


@dataclass(frozen=True, slots=True)
class DemoCaseSeedResult:
    understanding_key: str
    created: bool


@dataclass(frozen=True, slots=True)
class DemoSeedSummary:
    tenant_id: str
    no_strong_identifier: DemoCaseSeedResult
    matching_strong_identifier: DemoCaseSeedResult
    conflicting_strong_identifiers: DemoCaseSeedResult


class DemoEntityResolutionSeeder:
    """Test-covered in test_demo_entity_resolution_seeder.py and
    test_demo_entity_resolution_seeder_postgres.py."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def seed(self, tenant_id: str = BOOTSTRAP_DEMO_TENANT_ID) -> DemoSeedSummary:
        if tenant_id != BOOTSTRAP_DEMO_TENANT_ID:
            raise DemoTenantRequiredError(
                f"The demo Entity Resolution seeder refuses to seed tenant {tenant_id!r}; "
                f"it only ever seeds the labeled demo tenant {BOOTSTRAP_DEMO_TENANT_ID!r}."
            )

        self._seed_source_systems(tenant_id)
        self._seed_source_object(
            tenant_id, _CASE_A_CRM_OBJECT_ID, _CRM_SYSTEM_ID, "Demo CRM: TSMC (Case A)"
        )
        self._seed_source_object(
            tenant_id,
            _CASE_A_REGISTRY_OBJECT_ID,
            _REGISTRY_SYSTEM_ID,
            "Demo Registry: Taiwan Semiconductor Manufacturing Company Limited (Case A)",
        )
        self._seed_source_object(
            tenant_id, _CASE_B_CRM_OBJECT_ID, _CRM_SYSTEM_ID, "Demo CRM: TSMC (Case B)"
        )
        self._seed_source_object(
            tenant_id,
            _CASE_B_REGISTRY_OBJECT_ID,
            _REGISTRY_SYSTEM_ID,
            "Demo Registry: Taiwan Semiconductor Manufacturing Company Limited (Case B)",
        )
        self._seed_source_object(
            tenant_id, _CASE_C_CRM_OBJECT_ID, _CRM_SYSTEM_ID, "Demo CRM: TSMC (Case C)"
        )
        self._seed_source_object(
            tenant_id,
            _CASE_C_REGISTRY_OBJECT_ID,
            _REGISTRY_SYSTEM_ID,
            "Demo Registry: Taiwan Semiconductor Manufacturing Company Limited (Case C)",
        )
        self._seed_enterprise_entity(tenant_id, _CASE_A_ENTITY_ID, "Demo Candidate: TSMC (Case A)")
        self._seed_enterprise_entity(tenant_id, _CASE_B_ENTITY_ID, "Demo Candidate: TSMC (Case B)")
        self._session.flush()

        policy = conservative_preset()
        policy_row = ResolutionPolicyStore(self._session).materialize(
            tenant_id, policy, preset_kind="Conservative"
        )
        engine = EvidenceResolutionEngine(policy, policy_id=policy_row.policy_id)

        result_a = self._seed_case(
            tenant_id=tenant_id,
            engine=engine,
            crm_object_id=_CASE_A_CRM_OBJECT_ID,
            registry_object_id=_CASE_A_REGISTRY_OBJECT_ID,
            crm_tax_id=None,
            registry_tax_id=None,
            candidate_entity_id=_CASE_A_ENTITY_ID,
        )
        result_b = self._seed_case(
            tenant_id=tenant_id,
            engine=engine,
            crm_object_id=_CASE_B_CRM_OBJECT_ID,
            registry_object_id=_CASE_B_REGISTRY_OBJECT_ID,
            crm_tax_id=_MATCHING_TAX_ID,
            registry_tax_id=_MATCHING_TAX_ID,
            candidate_entity_id=_CASE_B_ENTITY_ID,
        )
        result_c = self._seed_case(
            tenant_id=tenant_id,
            engine=engine,
            crm_object_id=_CASE_C_CRM_OBJECT_ID,
            registry_object_id=_CASE_C_REGISTRY_OBJECT_ID,
            crm_tax_id=_CONFLICTING_TAX_ID_CRM,
            registry_tax_id=_CONFLICTING_TAX_ID_REGISTRY,
            candidate_entity_id=None,
        )

        return DemoSeedSummary(
            tenant_id=tenant_id,
            no_strong_identifier=result_a,
            matching_strong_identifier=result_b,
            conflicting_strong_identifiers=result_c,
        )

    # -- provenance -----------------------------------------------------

    def _seed_source_systems(self, tenant_id: str) -> None:
        if self._session.get(SourceSystem, _CRM_SYSTEM_ID) is None:
            self._session.add(
                SourceSystem(
                    source_system_id=_CRM_SYSTEM_ID,
                    tenant_id=tenant_id,
                    source_system_name="Demo CRM",
                    lifecycle_state="Active",
                    effective_from=SEED_TIMESTAMP,
                    governance_status="Approved",
                    created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                    created_on=SEED_TIMESTAMP,
                )
            )
        if self._session.get(SourceSystem, _REGISTRY_SYSTEM_ID) is None:
            self._session.add(
                SourceSystem(
                    source_system_id=_REGISTRY_SYSTEM_ID,
                    tenant_id=tenant_id,
                    source_system_name="Demo Corporate Registry",
                    lifecycle_state="Active",
                    effective_from=SEED_TIMESTAMP,
                    governance_status="Approved",
                    created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                    created_on=SEED_TIMESTAMP,
                )
            )
        self._session.flush()

    def _seed_source_object(
        self, tenant_id: str, object_id: UUID, system_id: UUID, name: str
    ) -> None:
        if self._session.get(SourceObject, object_id) is not None:
            return
        self._session.add(
            SourceObject(
                source_object_id=object_id,
                tenant_id=tenant_id,
                source_object_name=name,
                lifecycle_state="Active",
                effective_from=SEED_TIMESTAMP,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=SEED_TIMESTAMP,
                source_system_id=system_id,
            )
        )

    def _seed_enterprise_entity(self, tenant_id: str, entity_id: UUID, name: str) -> None:
        if self._session.get(EnterpriseEntity, entity_id) is not None:
            return
        self._session.add(
            EnterpriseEntity(
                enterprise_entity_id=entity_id,
                tenant_id=tenant_id,
                enterprise_entity_name=name,
                lifecycle_state="Active",
                effective_from=SEED_TIMESTAMP,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=SEED_TIMESTAMP,
                entity_type_id=BOOTSTRAP_ENTITY_TYPE_ID,
                business_domain_id=BOOTSTRAP_BUSINESS_DOMAIN_ID,
            )
        )

    # -- cases ------------------------------------------------------------

    def _seed_case(
        self,
        *,
        tenant_id: str,
        engine: EvidenceResolutionEngine,
        crm_object_id: UUID,
        registry_object_id: UUID,
        crm_tax_id: str | None,
        registry_tax_id: str | None,
        candidate_entity_id: UUID | None,
    ) -> DemoCaseSeedResult:
        source_object_ids = (crm_object_id, registry_object_id)
        understanding_key = EntityResolutionStore.understanding_key(source_object_ids)
        store = EntityResolutionStore(self._session)
        if store.get_current_record(tenant_id, understanding_key) is not None:
            return DemoCaseSeedResult(understanding_key=understanding_key, created=False)

        representations = (
            SourceRepresentation(
                source_object_id=crm_object_id,
                source_system_name="Demo CRM",
                display_name="TSMC",
                acronym="TSMC",
                website_domain="tsmc.com",
                country="Taiwan",
                strong_identifiers=(
                    ((EvidenceType.STRONG_IDENTIFIER_TAX_REGISTRATION, crm_tax_id),)
                    if crm_tax_id
                    else ()
                ),
            ),
            SourceRepresentation(
                source_object_id=registry_object_id,
                source_system_name="Demo Corporate Registry",
                display_name=CANDIDATE_NAME,
                website_domain="tsmc.com",
                country="Taiwan",
                strong_identifiers=(
                    ((EvidenceType.STRONG_IDENTIFIER_TAX_REGISTRATION, registry_tax_id),)
                    if registry_tax_id
                    else ()
                ),
            ),
        )
        record = engine.resolve(
            tenant_id=tenant_id,
            supporting_source_object_ids=source_object_ids,
            representations=representations,
            candidate_name=CANDIDATE_NAME,
            candidate_enterprise_entity_id=candidate_entity_id,
            produced_at=SEED_TIMESTAMP,
            candidate_country="Taiwan",
        )
        store.append(record)
        return DemoCaseSeedResult(understanding_key=understanding_key, created=True)


if __name__ == "__main__":
    from app.core.config import get_settings
    from app.infrastructure.persistence.database import create_database_engine
    from app.infrastructure.persistence.session import create_session_factory

    settings = get_settings()
    engine = create_database_engine(settings)
    sessions = create_session_factory(engine)
    with sessions.begin() as cli_session:
        result = DemoEntityResolutionSeeder(cli_session).seed()
    print(result)
