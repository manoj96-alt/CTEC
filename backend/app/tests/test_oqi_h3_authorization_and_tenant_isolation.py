"""CDD-049 OQI-H3 Governed Conformity and Canonical Standards -- Artifact
Authorization row 10: authorization-separation and tenant-isolation
adversarial tests for `oqi-canonical-standard:configure` and shared-standard
read access (CDD-049 §9, §25, §32 T1-T3).

CDD-049 §25/§26 is explicit and binding: **H3 authorizes no public
configuration API of any kind.** `oqi-canonical-standard:configure`'s
enforcement is service-level only -- declared in the realm so the authority
exists and is provably distinct from every other OQI scope, but with no
route to gate today (mirroring CDD-047 §22's own `oqi-coverage:configure`
precedent exactly, CDD-049 §25). This file proves the matrix's T1-T3 honestly
under that disclosed architecture rather than fabricating a route-level
enforcement test for a route that does not exist:

  T1: a `CanonicalStandard` genuinely carries no `tenant_id` (shared-
      platform, CDD-049 §9) and is correctly consulted by two independent
      tenants' own Conformity evaluations, each producing its own,
      correctly tenant-scoped `QualityFinding` -- real PostgreSQL.
  T2: "unauthorized configuration rejected" under H3's own disclosed
      no-route architecture means there is no live application-boundary
      write path today that could be tricked into granting canonical-
      standard authority via a wrong scope -- proven structurally: the
      scope literal appears in the realm configuration and nowhere in
      `app/api/`, and no CanonicalStandard CRUD route/schema exists
      (CDD-049 §26's own explicit callout, verified fresh this phase).
  T3: `oqi-canonical-standard:configure` is a distinct string, never equal
      to and never substitutable by `oqi-remediation:authorize`,
      `oqi-remediation:report-execution`, `oqi-reference-evidence:configure`,
      `oqi-reference-evidence:verify`, `oqi-coverage:configure`, or
      `oqi:read` -- CONFIGURATION AUTHORITY != REMEDIATION AUTHORITY,
      preserved structurally, identical to every prior OQI-family
      scope-separation precedent."""

# isort: skip_file
from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, inspect, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_conformity_evaluation_service import OqiConformityEvaluationService
from app.domain.oqi.quality_rule import (
    QualityDimension,
    QualityFindingType,
    QualityRule,
    QualityRuleStatus,
)
from app.domain.oqi_canonical_standard.standard import (
    CanonicalAlias,
    CanonicalStandard,
    CanonicalStandardStatus,
    CanonicalValue,
)
from app.infrastructure.persistence.models.oqi_canonical_standard import CanonicalStandardORM
from app.infrastructure.persistence.models.oqi_quality_finding import QualityFindingORM
from app.infrastructure.persistence.oqi_canonical_standard_repository import (
    OqiCanonicalStandardRepositoryImpl,
    OQI_CANONICAL_STANDARD_ADVISORY_LOCK_SEED,
)
from app.infrastructure.persistence.oqi_conformity_evaluation_repository import (
    OqiConformityEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_rule_repository import OqiQualityRuleRepositoryImpl
from app.tests.test_oqi_h3_conformity_crown import NOW, _seed_information_element, _tenant
from app.tests.test_oqi_quality_postgres import _admit_evidence, _subject
from app.tests.test_oqi_quality_postgres import _seed_field as _seed_oqi1_field

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
REALM_CONFIG_PATH = REPOSITORY_ROOT / "keycloak" / "ctec-realm.json"
CANONICAL_STANDARD_CONFIGURE_SCOPE = "oqi-canonical-standard:configure"

_OTHER_OQI_SCOPES = (
    "oqi:read",
    "oqi-remediation:authorize",
    "oqi-remediation:report-execution",
    "oqi-reference-evidence:configure",
    "oqi-reference-evidence:verify",
    "oqi-coverage:configure",
)


def _realm_config() -> dict[str, Any]:
    result: dict[str, Any] = json.loads(REALM_CONFIG_PATH.read_text())
    return result


class TestCanonicalStandardScopeRegistration:
    def test_scope_is_declared_exactly_once(self) -> None:
        client_scopes = _realm_config()["clientScopes"]
        matches = [s for s in client_scopes if s["name"] == CANONICAL_STANDARD_CONFIGURE_SCOPE]
        assert len(matches) == 1

    def test_scope_description_is_bounded(self) -> None:
        client_scopes = _realm_config()["clientScopes"]
        scope = next(s for s in client_scopes if s["name"] == CANONICAL_STANDARD_CONFIGURE_SCOPE)
        assert len(scope["description"]) <= 255

    def test_scope_is_optional_never_default(self) -> None:
        realm = _realm_config()
        for client in realm.get("clients", []):
            default_scopes = client.get("defaultClientScopes", [])
            assert CANONICAL_STANDARD_CONFIGURE_SCOPE not in default_scopes, (
                f"{CANONICAL_STANDARD_CONFIGURE_SCOPE} must never be a default scope "
                f"(client {client.get('clientId')!r})"
            )
        optional_holders = [
            client
            for client in realm.get("clients", [])
            if CANONICAL_STANDARD_CONFIGURE_SCOPE in client.get("optionalClientScopes", [])
        ]
        assert optional_holders  # at least one client declares it optional


class TestT2NoLiveConfigurationRoute:
    """CDD-049 §25-§26: H3 authorizes no public configuration API. Proven
    structurally, not by a 403 against a route that does not exist."""

    def test_scope_literal_appears_in_no_api_module(self) -> None:
        api_dir = REPOSITORY_ROOT / "backend" / "app" / "api"
        offending = [
            path
            for path in api_dir.rglob("*.py")
            if CANONICAL_STANDARD_CONFIGURE_SCOPE in path.read_text()
        ]
        assert (
            offending == []
        ), f"no route may gate on {CANONICAL_STANDARD_CONFIGURE_SCOPE} today: {offending}"

    def test_no_canonical_standard_route_or_schema_exists(self) -> None:
        router_source = (
            REPOSITORY_ROOT / "backend" / "app" / "api" / "oqi" / "router.py"
        ).read_text()
        schemas_source = (
            REPOSITORY_ROOT / "backend" / "app" / "api" / "oqi" / "schemas.py"
        ).read_text()
        assert "canonical" not in router_source.lower()
        assert "canonical" not in schemas_source.lower()

    def test_repository_write_methods_carry_no_bypassable_authorization_hook(self) -> None:
        """The repository itself performs plain, ungated inserts (CDD-049
        §25: enforcement belongs at a future application boundary, never
        embedded ad hoc in the repository) -- confirmed here so a reader
        does not mistake the repository's own advisory lock (identity
        serialization only) for an authorization check."""
        import inspect

        source = inspect.getsource(OqiCanonicalStandardRepositoryImpl.insert_standard)
        assert "scope" not in source.lower()
        assert "principal" not in source.lower()


class TestT3ConfigurationAuthorityDistinctFromEveryOtherScope:
    def test_scope_string_is_unique_among_oqi_scopes(self) -> None:
        assert CANONICAL_STANDARD_CONFIGURE_SCOPE not in _OTHER_OQI_SCOPES
        for other in _OTHER_OQI_SCOPES:
            assert CANONICAL_STANDARD_CONFIGURE_SCOPE != other

    def test_advisory_lock_seed_is_distinct_from_every_other_oqi_seed(self) -> None:
        assert OQI_CANONICAL_STANDARD_ADVISORY_LOCK_SEED == 7
        assert OQI_CANONICAL_STANDARD_ADVISORY_LOCK_SEED not in {1, 2, 3, 4, 5, 6}


# ---------------------------------------------------------------------
# T1: shared-standard, real-PostgreSQL tenant isolation.
# ---------------------------------------------------------------------


@pytest.fixture(scope="module")
def factory(migrated_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=migrated_engine)


@pytest.fixture()
def session(factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    with factory() as session:
        yield session
        session.rollback()


def _conformity_rule(
    *, quality_condition_id: str, information_element_requirement_id: UUID
) -> QualityRule:
    return QualityRule.new(
        quality_condition_id=quality_condition_id,
        version=1,
        dimension=QualityDimension.CONFORMITY,
        finding_type=QualityFindingType.NON_CANONICAL_REPRESENTATION,
        validity_primitive=None,
        information_element_requirement_id=str(information_element_requirement_id),
        rule_parameters={},
        status=QualityRuleStatus.ACTIVE,
        created_by="steward",
        created_on=NOW,
    )


class TestT1SharedStandardTenantEvaluation:
    def test_canonical_standard_orm_carries_no_tenant_id_column(self) -> None:
        columns = {column.name for column in inspect(CanonicalStandardORM).columns}
        assert "tenant_id" not in columns  # genuinely shared-platform, CDD-049 §9

    def test_two_tenants_share_one_standard_each_gets_its_own_finding(
        self, session: Session
    ) -> None:
        ier_id = _seed_information_element(session)
        value_id = uuid4()
        standard_id = uuid4()
        standard = CanonicalStandard(
            canonical_standard_id=standard_id,
            information_element_requirement_id=ier_id,
            version_number=1,
            previous_version_id=None,
            status=CanonicalStandardStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
            values=(
                CanonicalValue(
                    canonical_value_id=value_id,
                    canonical_standard_id=standard_id,
                    canonical_representation="USA",
                    aliases=(
                        CanonicalAlias(
                            canonical_alias_id=uuid4(),
                            canonical_value_id=value_id,
                            alias_representation="US",
                        ),
                    ),
                ),
            ),
        )
        OqiCanonicalStandardRepositoryImpl(session).insert_standard(standard)
        session.flush()

        tenant_a = _tenant()
        tenant_b = _tenant()
        service = OqiConformityEvaluationService(
            evaluation_repository=OqiConformityEvaluationRepositoryImpl(session),
            canonical_standard_lookup=OqiCanonicalStandardRepositoryImpl(session),
            clock=lambda: NOW,
        )

        # Tenant A: canonical observation -- SATISFIED.
        a_object, a_field = _seed_oqi1_field(
            session, tenant_id=tenant_a, field_label="MFG-COUNTRY-A"
        )
        _admit_evidence(
            session,
            source_field_id=a_field,
            source_record_reference="rec-a",
            observed_representation="USA",
        )
        a_rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(a_rule)
        session.flush()
        a_subject = _subject(
            tenant_id=tenant_a,
            source_object_id=a_object,
            source_field_id=a_field,
            reference="rec-a",
        )
        a_evaluation = service.evaluate_current_state(rule=a_rule, subject=a_subject)
        session.flush()
        assert a_evaluation is not None
        assert a_evaluation.outcome.value == "SATISFIED"

        # Tenant B: alias observation, against the SAME shared standard --
        # VIOLATED, entirely independently of Tenant A.
        b_object, b_field = _seed_oqi1_field(
            session, tenant_id=tenant_b, field_label="MFG-COUNTRY-B"
        )
        _admit_evidence(
            session,
            source_field_id=b_field,
            source_record_reference="rec-b",
            observed_representation="US",
        )
        b_rule = _conformity_rule(
            quality_condition_id=f"cond-{uuid4()}", information_element_requirement_id=ier_id
        )
        OqiQualityRuleRepositoryImpl(session).create(b_rule)
        session.flush()
        b_subject = _subject(
            tenant_id=tenant_b,
            source_object_id=b_object,
            source_field_id=b_field,
            reference="rec-b",
        )
        b_evaluation = service.evaluate_current_state(rule=b_rule, subject=b_subject)
        session.flush()
        assert b_evaluation is not None
        assert b_evaluation.outcome.value == "VIOLATED"

        # Each tenant's own Finding is genuinely scoped to that tenant --
        # Tenant A's query never sees Tenant B's Finding and vice versa.
        a_findings = (
            session.execute(
                select(QualityFindingORM).where(QualityFindingORM.tenant_id == tenant_a)
            )
            .scalars()
            .all()
        )
        b_findings = (
            session.execute(
                select(QualityFindingORM).where(QualityFindingORM.tenant_id == tenant_b)
            )
            .scalars()
            .all()
        )
        assert a_findings == []  # SATISFIED -- zero Findings for Tenant A
        assert len(b_findings) == 1
        assert b_findings[0].tenant_id == tenant_b

        # Both evaluations consulted the exact same standard/version --
        # proving it is one genuinely shared row, not per-tenant duplicated.
        active = OqiCanonicalStandardRepositoryImpl(
            session
        ).get_active_standard_for_information_element(information_element_requirement_id=ier_id)
        assert active is not None
        assert active.canonical_standard_id == standard_id
        count = (
            session.execute(
                select(CanonicalStandardORM).where(
                    CanonicalStandardORM.information_element_requirement_id == ier_id
                )
            )
            .scalars()
            .all()
        )
        assert len(count) == 1  # exactly one row serves both tenants
